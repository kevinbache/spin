import json
from pathlib import Path
from typing import Text, List

from spin import utils
from spin.ssh import SshKeyOnDisk


class _KubernetesObject(utils.ShellRunnerMixin):
    def __init__(self, object_type: Text, name: Text, verbose=True):
        super().__init__(verbose)
        self._object_type = object_type
        self.name = name

    def create(self):
        # https://stackoverflow.com/questions/52901435/how-i-create-new-namespace-in-kubernetes
        self._run(f'kubectl create {self._object_type} {self.name}')

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
    def __init__(self, name: Text, files: List[Path], verbose=True):
        super().__init__(object_type='secret', name=name, verbose=verbose)
        self.name = name
        self.files = files

    @classmethod
    def from_ssh_keys(cls, secret_name: Text, ssh_keys: List[SshKeyOnDisk]):
        files = []
        for key in ssh_keys:
            files.append(key.public_key_path)
            files.append(key.private_key_path)
        return cls(name=secret_name, files=files)

    def create(self):
        file_strs = []
        for f in self.files:
            if not f.exists():
                raise IOError(f"Trying to create secret from nonexistent file: {f}")
            file_strs.append(f'--from-file={f}')
        all_files_str = ' '.join(file_strs)
        cmd = f'kubectl create secret generic {self.name} {all_files_str}'
        self._run(cmd)


if __name__ == '__main__':
    secret = KubernetesSecret(name='spin-workbench-ssh-server-keys', files=[])
    print(secret.list())
    print(secret.list_names())
    print(secret.exists())
    secret.delete()
    print(secret.exists())

    namespace = KubernetesNamespace(name='blah')
    print(namespace.list())
    print(namespace.list_names())
    print(namespace.exists())
    namespace.delete()
    print(namespace.exists())

