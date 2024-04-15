# Setup notes

## k3s

This repo assumes kubernetes is installed on the server running the dashboard api etc. K3s is a good option for this.

K3s uses containerd, so images in the docker image store aren't available to k3s. To get around this, images need to be pulled from a registry.

The `deploy` folder contains manifests for deploying a docker registry to the k3s cluster.
To push to this registry, the docker daemon on the server needs to allow non-HTTPs. This can be done by adding the registry to the `insecure-registries` list in `/etc/docker/daemon.json` and restarting the docker service.


To enable k3s to pull from the registry via HTTPs, create a file in `/etc/rancher/k3s/registries.yaml` with the following content:

```yaml
mirrors:
  pibell-0.lan:5000:
    endpoint:
      - "http://pibell-0.lan:5000"
```

Then `sudo systemctl restart k3s` to apply the changes.

## credentials

Create a k8s secret for the leaf service credentials:

`kubectl create secret generic leaf-creds --from-literal=password='<password>' --from-literal=user='<username>'`

Create a k8s secret for the weather API:

`kubectl create secret generic weather-creds --from-literal=api-key='<api-key>' --from-literal=lat='<latitude>' --from-literal=lon='<longitude>'`

Create a secret for the app insights connection string

`kubectl create secret generic dash-api-app-insights --from-literal=connection_string='<connection_string>'`


## leaf-status

To test the cronjob, create a job derived from it: `kubectl create job --from=cronjob/leaf-status leaf-status-test`

## dash-api

Download FiraCode-Regular.ttf and place in a `fonts` directory under `dash-api`.




