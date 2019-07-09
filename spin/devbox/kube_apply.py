#!/usr/bin/python3
# coding: utf-8
# __________   ________________________________________________   #
# kube_apply - apply Yaml similar to kubectl apply -f file.yaml   #
#                                                                 #
# (C) 2019 Hermann Vosseler <Ichthyostega@web.de>                 #
# This is OpenSource software; licensed under Apache License v2+  #
# ############################################################### #
# ref:
#   https://stackoverflow.com/questions/36307950/kubernetes-api-call-equivalent-to-kubectl-apply
'''
Utility for the official Kubernetes python client: apply Yaml data.
While still limited to some degree, this utility attempts to provide
functionality similar to `kubectl apply -f`
- load and parse Yaml
- try to figure out the object type and API to use
- figure out if the resource already exists, in which case
  it needs to be patched or replaced alltogether.
- otherwise just create a new resource.

Based on inspiration from `kubernetes/utils/create_from_yaml.py`

@since: 2/2019
@author: Ichthyostega
'''


import re
import yaml
import logging

import kubernetes.client
import kubernetes.config



def _run_usage_example():
    ''' demonstrate usage by creating a simple Pod through default client
    '''
    logging.basicConfig(level=logging.DEBUG)
    #
#   KUBECONFIG = '/path/to/special/kubecfg.yaml'
#   import kubernetes.config
#   client = kubernetes.config.new_client_from_config(config_file=KUBECONFIG)
#   # --or alternatively--
#   kubernetes.config.load_kube_config(config_file=KUBECONFIG)


    from_yaml('''
kind: Pod
apiVersion: v1
metadata:
  name: dummy-pod
  labels:
    blow: job
spec:
  containers:
  - name: sleepr
    image: busybox
    command:
    - /bin/sh
    - -c
    - sleep 24000
''')


def from_yaml(rawData, client=None, namespace='default', **kwargs):
    ''' invoke the K8s API to create or replace an object given as YAML spec.
        @param rawData: either a string or an opened input stream with a
                        YAML formatted spec, as you'd use for `kubectl apply -f`
        @param client: (optional) preconfigured client environment to use for invocation
        @param namespace: (optional) namespace in which to create these objects
        @param kwargs: (optional) further arguments to pass to the create/replace call
        @return: response object from Kubernetes API call
    '''
    kubernetes.config.load_kube_config()
    for obj in yaml.load_all(rawData, Loader=yaml.SafeLoader):
        _create_or_update_or_replace(obj, namespace, client, **kwargs)


def _create_or_update_or_replace(obj, namespace, client=None, **kwargs):
    ''' invoke the K8s API to create or replace a kubernetes object.
        The first attempt is to create(insert) this object; when this is rejected because
        of an existing object with same name, we attempt to patch this existing object.
        As a last resort, if even the patch is rejected, we *delete* the existing object
        and recreate from scratch.
        @param obj: complete object specification, including API version and metadata.
        @param client: (optional) preconfigured client environment to use for invocation
        @param kwargs: (optional) further arguments to pass to the create/replace call
        @return: response object from Kubernetes API call
    '''
    k8sApi = _find_k8s_api(obj, client)
    try:
        res = _invoke_api(k8sApi, 'create', obj, namespace, **kwargs)
        logging.debug('K8s: %s created -> uid=%s', _describe(obj), res.metadata.uid)
    except kubernetes.client.rest.ApiException as apiEx:
        if apiEx.reason != 'Conflict': raise
        try:
            # asking for forgiveness...
            res = _invoke_api(k8sApi, 'patch', obj, namespace, **kwargs)
            logging.debug('K8s: %s PATCHED -> uid=%s', _describe(obj), res.metadata.uid)
        except kubernetes.client.rest.ApiException as apiEx:
            if apiEx.reason != 'Unprocessable Entity':
                raise ValueError(f"{apiEx.reason}")
            try:
                # second attempt... delete the existing object and re-insert
                logging.debug('K8s: replacing %s FAILED. Attempting deletion and recreation...', _describe(obj))
                res = _invoke_api(k8sApi, 'delete', obj, namespace, **kwargs)
                logging.debug('K8s: %s DELETED...', _describe(obj))
                res = _invoke_api(k8sApi, 'create', obj, namespace, **kwargs)
                logging.debug('K8s: %s CREATED -> uid=%s', _describe(obj), res.metadata.uid)
            except Exception as ex:
                message = 'K8s: FAILURE updating %s. Exception: %s' % (_describe(obj), ex)
                logging.error(message)
                raise RuntimeError(message)
    return res


def _patch_object(obj, namespace, client=None, **kwargs):
    k8sApi = _find_k8s_api(obj, client)
    try:
        res = _invoke_api(k8sApi, 'patch', obj, namespace, **kwargs)
        logging.debug('K8s: %s PATCHED -> uid=%s', _describe(obj), res.metadata.uid)
        return res
    except kubernetes.client.rest.ApiException as apiEx:
        if apiEx.reason == 'Unprocessable Entity':
            message = 'K8s: patch for %s rejected. Exception: %s' % (_describe(obj), apiEx)
            logging.error(message)
            raise RuntimeError(message)
        else:
            raise


def _delete_object(obj, namespace, client=None, **kwargs):
    k8sApi = _find_k8s_api(obj, client)
    try:
        res = _invoke_api(k8sApi, 'delete', obj, namespace, **kwargs)
        logging.debug('K8s: %s DELETED. uid was: %s', _describe(obj), res.details and res.details.uid or '?')
        return True
    except kubernetes.client.rest.ApiException as apiEx:
        if apiEx.reason == 'Not Found':
            logging.warning('K8s: %s does not exist (anymore).', _describe(obj))
            return False
        else:
            message = 'K8s: deleting %s FAILED. Exception: %s' % (_describe(obj), apiEx)
            logging.error(message)
            raise RuntimeError(message)



def _find_k8s_api(obj, client=None):
    ''' Investigate the object spec and lookup the corresponding API object
        @param client: (optional) preconfigured client environment to use for invocation
        @return: a client instance wired to the apriopriate API
    '''
    grp, _, ver = obj['apiVersion'].partition('/')
    if ver == '':
        ver = grp
        grp = 'core'
    # Strip 'k8s.io', camel-case-join dot separated parts. rbac.authorization.k8s.io -> RbacAuthorzation
    grp = ''.join(part.capitalize() for part in grp.rsplit('.k8s.io', 1)[0].split('.'))
    ver = ver.capitalize()

    k8sApi = '%s%sApi' % (grp, ver)
    return getattr(kubernetes.client, k8sApi)(client)


def _invoke_api(k8sApi, action, obj, namespace='default', **kwargs):
    ''' find a suitalbe function and perform the actual API invocation.
        @param k8sApi: client object for the invocation, wired to correct API version
        @param action: either 'create' (to inject a new objet) or 'replace','patch','delete'
        @param obj: the full object spec to be passed into the API invocation
        @param kwargs: (optional) extraneous arguments to pass
        @return: response object from Kubernetes API call
    '''
    # transform ActionType from Yaml into action_type for swagger API
    kind = _camel2snake(obj['kind'])
    # determine namespace to place the object in, supply default
    # try: namespace = obj['metadata']['namespace']
    # except: namespace = 'default'

    functionName = '%s_%s' %(action,kind)
    if hasattr(k8sApi, functionName):
        # namespace agnostic API
        function = getattr(k8sApi, functionName)
    else:
        functionName = '%s_namespaced_%s' %(action,kind)
        function = getattr(k8sApi, functionName)
        kwargs['namespace'] = namespace
    if not 'create' in functionName:
        kwargs['name'] = obj['metadata']['name']
    if 'delete' in functionName:
        from kubernetes.client.models.v1_delete_options import V1DeleteOptions
        obj = V1DeleteOptions()

    return function(body=obj, **kwargs)


def _describe(obj):
    return "%s '%s'" % (obj['kind'], obj['metadata']['name'])


def _camel2snake(string):
    string = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    string = re.sub('([a-z0-9])([A-Z])', r'\1_\2', string).lower()
    return string


if __name__=='__main__':
    _run_usage_example()
