# Kubernetes Deployment

Deploys network-buoy as a single-replica Deployment exposed via a LoadBalancer Service. Works on any K8s cluster; the Service has NLB annotations for AWS EKS out of the box.

---

## Prerequisites

- `kubectl` connected to your cluster (`kubectl cluster-info` works)
- A container registry the cluster can pull from (ECR, GCR, GHCR, Docker Hub)
- Persistent storage available (default StorageClass, or `gp2` on EKS)
- On EKS: AWS Load Balancer Controller installed (for the NLB annotation)

---

## One-time setup

### 1. Push the image

```bash
# Example for ECR
REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com

aws ecr get-login-password | docker login --username AWS --password-stdin $REGISTRY
docker build -t $REGISTRY/network-buoy:latest .
docker push $REGISTRY/network-buoy:latest
```

### 2. Set your registry in the manifests

```bash
# In deploy/k8s/
sed -i "s|REGISTRY|$REGISTRY|g" deployment.yaml kustomization.yaml
```

Or use kustomize to set it per environment:

```bash
cd deploy/k8s
kustomize edit set image REGISTRY/network-buoy=$REGISTRY/network-buoy:latest
```

---

## Deploy

```bash
kubectl apply -k deploy/k8s/
```

This creates (in order):
1. `network-buoy` namespace
2. PersistentVolumeClaims — `network-buoy-logs` (5 Gi) and `network-buoy-ollama` (10 Gi)
3. Deployment — 1 replica, all 19 ports
4. Service — LoadBalancer with all 19 ports mapped

Check rollout:

```bash
kubectl rollout status deployment/network-buoy -n network-buoy
kubectl get svc network-buoy -n network-buoy  # wait for EXTERNAL-IP
```

---

## NODE_ID

`NODE_ID` is set from `metadata.name` (the pod name) by default — see `deployment.yaml`. This means:

- Each pod has a stable identity across its own restarts (same pod name = same fake hostname, IPs, banners)
- If you scale to multiple replicas, each pod gets a different identity automatically, which is correct — you want each honeypot node to look distinct

To override with a fixed string instead:

```yaml
# In deployment.yaml, replace the fieldRef block with:
- name: NODE_ID
  value: "prod-honeypot-east-01"
```

---

## StorageClass

The PVCs in `pvc.yaml` use the cluster's default StorageClass. On EKS you likely want `gp2` or `gp3`:

```yaml
# Uncomment in pvc.yaml:
storageClassName: gp2
```

On GKE use `standard` or `premium-rwo`. On AKS use `managed-premium`.

---

## Reading logs

```bash
# Stream live logs from the pod
kubectl logs -f deployment/network-buoy -n network-buoy

# Credential captures only
kubectl logs deployment/network-buoy -n network-buoy \
  | grep '"event":"credential"'

# Or exec into the pod and read the file directly
kubectl exec -it deployment/network-buoy -n network-buoy -- \
  grep '"event":"credential"' /data/honeypot.log
```

---

## Updating the image

```bash
docker build -t $REGISTRY/network-buoy:v2 .
docker push $REGISTRY/network-buoy:v2

kubectl set image deployment/network-buoy \
  network-buoy=$REGISTRY/network-buoy:v2 \
  -n network-buoy

kubectl rollout status deployment/network-buoy -n network-buoy
```

Or via kustomize:

```bash
cd deploy/k8s
kustomize edit set image REGISTRY/network-buoy=$REGISTRY/network-buoy:v2
kubectl apply -k .
```

---

## Teardown

```bash
kubectl delete -k deploy/k8s/
# PVCs are not deleted by kustomize — do this explicitly if you want to wipe logs:
kubectl delete pvc -n network-buoy --all
```

---

## Notes

- The liveness probe checks TCP port 80. The pod won't be marked ready until Ollama finishes pulling `gemma3:1b` (~800 MB) and the buoy starts listening — this takes 60–120 s on first boot. `initialDelaySeconds: 120` covers this.
- The Ollama model is stored on the `network-buoy-ollama` PVC so it survives pod restarts without re-downloading.
- On EKS, the `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation provisions a Network Load Balancer, which supports all TCP ports without an Ingress. If you're not on EKS, remove those two annotations — the cloud provider will use its default LoadBalancer implementation.
- Port 6443 (fake Kubernetes API) may conflict with your actual cluster API server if the node runs on port 6443. Route it differently or omit that port if needed.
