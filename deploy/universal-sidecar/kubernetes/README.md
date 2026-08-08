# Kubernetes manifests

Apply order:

```bash
kubectl apply -f service.yaml
kubectl apply -f networkpolicy.yaml
kubectl apply -f deployment.yaml
```

Create secret first:

```bash
kubectl create secret generic keprix-sidecar-secrets \
  --from-literal=token-secret='replace-me'
```

Service type is **ClusterIP** only. Do not change to LoadBalancer / NodePort
without TLS, auth, and NetworkPolicy review.
