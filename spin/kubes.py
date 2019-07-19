import abc
import json
import subprocess
import time
from pathlib import Path
from typing import Text, List, Iterable, Tuple, Dict

import yaml

from spin import utils
from spin.ssh import SshKeyOnDisk


class _KubernetesObject(utils.ShellRunnerMixin):
    def __init__(self, object_type: Text, name: Text, verbose=True):
        super().__init__(verbose)
        self._object_type = object_type
        self.name = name

    def create(self):
        # https://stackoverflow.com/questions/52901435/how-i-create-new-namespace-in-kubernetes
        return self._run(f'kubectl create {self._object_type} {self.name}')

    def delete(self, error_if_does_not_exist=False):
        if not self.exists():
            if error_if_does_not_exist:
                raise ValueError(
                    f"Tried to delete kubernetes {self._object_type} named {self.name} but it doesn't exist"
                )
            else:
                return self.EMPTY_RUN_RETURN_VALUE
        self._run(f'kubectl delete {self._object_type} {self.name}')

    def list(self):
        _, out, _ = self._run(f'kubectl get {self._object_type} -o json')
        out = json.loads(out)
        return out['items']

    def list_names(self):
        objs = self.list()
        return [obj['metadata']['name'] for obj in objs]

    def exists(self):
        return self.name in self.list_names()


class KubernetesNamespace(_KubernetesObject):
    def __init__(self, name: Text, verbose=True):
        super().__init__(object_type='namespace', name=name, verbose=verbose)


class KubernetesSecret(_KubernetesObject):
    def __init__(self, name: Text, files: List[Path], mount_point_on_pod: Text, verbose=True):
        super().__init__(object_type='secret', name=name, verbose=verbose)
        self.mount_point_on_pod = mount_point_on_pod
        self.files = files

    @classmethod
    def from_ssh_keys(cls, secret_name: Text, mount_point_on_pod: Text, ssh_keys: List[SshKeyOnDisk]):
        files = []
        for key in ssh_keys:
            files.append(key.public_key_path)
            files.append(key.private_key_path)
        return cls(name=secret_name, mount_point_on_pod=mount_point_on_pod, files=files)

    def create(self):
        file_strs = []
        for f in self.files:
            if not f.exists():
                raise IOError(f"Trying to create secret from nonexistent file: {f}")
            file_strs.append(f'--from-file={f}')
        all_files_str = ' '.join(file_strs)
        cmd = f'kubectl create secret generic {self.name} {all_files_str}'
        return self._run(cmd)

    def to_volume_mount(self):
        return {
            # todo: convert this to volume_name? what would the point be?
            'name': self.name,
            'mountPath': self.mount_point_on_pod,
            'readOnly': True,
        }

    def to_volume(self):
        return {
            # todo: convert this to volume_name? what would the point be?
            'name': self.name,
            'secret': {
                'secretName': self.name,
            }
        }


class _KubernetesApplyObject(_KubernetesObject, abc.ABC):
    """A _KubernetesObject which creates via `kubectl apply`"""
    @abc.abstractmethod
    def _get_yaml(self):
        pass

    def create(self, dry_run=False):
        # https://kubernetes.io/docs/reference/kubectl/cheatsheet/#apply
        dry_run_str = '--dry-run ' if dry_run else ''
        yaml = self._get_yaml()
        cmd = f'cat <<EOF | kubectl apply {dry_run_str}-f - {yaml}EOF'
        if dry_run:
            print(f'create command: \n{cmd}')
        # you have to use subprocess.check_output rather than _run because this is a multiline command.
        #   ref: https://stackoverflow.com/questions/42312099/how-to-run-multi-line-bash-commands-inside-python
        #   it will throw an error on nonzero output code
        out = subprocess.check_output(cmd, shell=True)
        out = out.decode('utf-8')
        err = ''
        return 0, out, err


class KubernetesPort:
    def __init__(self, name: Text, external_port: int, pod_port: int, protocol: Text = 'TCP'):
        self.name = name
        self.external_port = external_port
        self.pod_port = pod_port
        self.protocol = protocol

    def to_container_port(self):
        return {'containerPort': self.pod_port}

    def to_service_port(self):
        return {
            'name': self.name,
            'port': self.external_port,
            'targetPort': self.pod_port,
            'protocol': self.protocol,
        }


class KubernetesDeployment(_KubernetesApplyObject):
    def __init__(
            self,
            name: Text,
            container_image_uri: Text,
            secrets: Iterable[KubernetesSecret] = (),
            ports: Iterable[KubernetesPort] = (),
            num_replicas=1,
    ):
        super().__init__(object_type='deployment', name=name)
        self.container_image_uri = container_image_uri
        self.secrets = secrets
        self.ports = ports
        self.num_replicas = num_replicas

    def _get_yaml(self):
        deployment_dict = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': self.name,
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'run': self.name,
                    }
                },
                'replicas': self.num_replicas,
                'template': {
                    'metadata': {
                        'labels': {
                            'run': self.name,
                        },
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': self.name,
                                'image': self.container_image_uri,
                            },
                        ],
                    },
                },
            },
        }

        pod_spec_dict = deployment_dict['spec']['template']['spec']
        container_dict = pod_spec_dict['containers'][0]
        if self.ports:
            container_dict['ports'] = [port.to_container_port() for port in self.ports]

        if self.secrets:
            container_dict['volumeMounts'] = [secret.to_volume_mount() for secret in self.secrets]
            if 'volumes' not in pod_spec_dict:
                pod_spec_dict['volumes'] = []
            pod_spec_dict['volumes'].extend([secret.to_volume() for secret in self.secrets])

        yaml_str = '\n' + yaml.dump(deployment_dict)
        return yaml_str


class KubernetesService(_KubernetesApplyObject):
    def __init__(self, name: Text, deployment_name: Text, ports: List[KubernetesPort]):
        super().__init__(object_type='service', name=name)
        self.deployment_name = deployment_name
        self.ports = ports

    def _get_yaml(self):
        service_dict = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': self.name,
                'labels': {
                    'run': self.deployment_name,
                }
            },
            'spec': {
                'type': 'LoadBalancer',
                'selector': {
                    'run': self.deployment_name,
                }
            }
        }
        if self.ports:
            service_dict['spec']['ports'] = [port.to_service_port() for port in self.ports]

        yaml_str = '\n' + yaml.dump(service_dict)
        return yaml_str

    def get_ip_and_ports(self, do_error_on_fail=False) -> Tuple[Text, Dict[Text, int]]:
        ip, ports_dict = self._get_ip_and_ports()
        if ip is None and do_error_on_fail:
            raise ValueError(f"Service, {self.name}, has no ip")

        while ip is None:
            time.sleep(5)
            if self.verbose:
                print(f"Waiting for service, {self.name}, to go live.  This may take about a minute.")
            ip, ports_dict = self._get_ip_and_ports()

        return ip, ports_dict

    def _get_ip_and_ports(self):
        """ Get the ip address and ports for the given service.

        Returns:
            ip address of the service endpoint and dict mapping service name to external port number
        """
        # get devbox ip address
        _, out, _ = self._run(f'kubectl get svc {self.name} -o json')
        out = json.loads(out)
        load_balancer_dict = out['status']['loadBalancer']
        if 'ingress' not in load_balancer_dict:
            return None, None
        ip = load_balancer_dict['ingress'][0]['ip']
        ports = out['spec']['ports']
        ports_dict = {port['name']: port['port'] for port in ports}
        return ip, ports_dict


def get_service_and_deployment(
        deployment_name: Text,
        container_image_uri: Text,
        service_name: Text,
        ports: List[KubernetesPort],
        secrets: List[KubernetesSecret],
        num_deployment_replicas: int = 1,
):
    """Get a paired deployment and service.  They won't be created.  Create your service first."""
    service = KubernetesService(
        name=service_name,
        deployment_name=deployment_name,
        ports=ports,
    )

    deployment = KubernetesDeployment(
        name=deployment_name,
        container_image_uri=container_image_uri,
        ports=ports,
        secrets=secrets,
        num_replicas=num_deployment_replicas,
    )
    return service, deployment


if __name__ == '__main__':
    secret = KubernetesSecret(name='spin-workbench-ssh-server-keys', files=[], mount_point_on_pod='/secrets/mnt/')
    print(secret.list())
    print(secret.list_names())
    print(secret.exists())
    secret.delete()
    print(secret.exists())

    # namespace = KubernetesNamespace(name='blah')
    # print(namespace.list())
    # print(namespace.list_names())
    # print(namespace.exists())
    # namespace.delete()
    # print(namespace.exists())

    ssh_port = KubernetesPort(name='ssh', external_port=22, pod_port=22)
    ports = [
        ssh_port,
        KubernetesPort(name='http', external_port=80, pod_port=80),
    ]

    # dep = KubernetesDeployment(
    #     name='my-workbench-deployment',
    #     container_image_uri='gcr.io/kb-experiment/devbox:latest',
    #     ports=ports,
    #     secrets=[secret],
    # )
    # print(dep.create(dry_run=True))
    # print(dep.list_names())

    service = KubernetesService(name='devbox-service', deployment_name='devbox', ports=ports)
    print(service.create(dry_run=False))
    print(service.list_names())

    ip, ports = service.get_ip_and_ports()
    print(ip)
    print(ports)

    # import yaml
    # print(yaml.dump(deployment))
