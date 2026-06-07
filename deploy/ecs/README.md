# ECS Fargate Deployment

Runs network-buoy as a single Fargate task with all 19 protocol listeners. Ollama runs inside the same container. Logs go to EFS (persisted) and CloudWatch (streaming).

---

## Prerequisites

- AWS CLI configured (`aws sts get-caller-identity` works)
- Docker installed locally
- An ECR repository named `network-buoy`
- An ECS cluster (create one if needed: `aws ecs create-cluster --cluster-name network-buoy`)
- An EFS file system for logs
- SSM Parameter Store entry for `NODE_ID`
- IAM roles: `ecsTaskExecutionRole` (standard) + `network-buoy-task-role` (needs SSM read)

---

## One-time setup

### 1. ECR repository

```bash
aws ecr create-repository --repository-name network-buoy --region us-east-1
```

### 2. NODE_ID in SSM

Pick any stable string — this determines the node's fake identity (hostname, IPs, banner content). Don't change it after deploy or the node will look different to returning attackers.

```bash
aws ssm put-parameter \
  --name /network-buoy/node-id \
  --value "prod-honeypot-01" \
  --type SecureString
```

### 3. EFS for logs

```bash
aws efs create-file-system --tags Key=Name,Value=network-buoy-logs
# Note the FileSystemId (fs-xxxxxxxx) — put it in task-definition.json
```

### 4. IAM task role

The task needs permission to read its own `NODE_ID` from SSM:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameters", "ssm:GetParameter"],
      "Resource": "arn:aws:ssm:REGION:ACCOUNT_ID:parameter/network-buoy/*"
    }
  ]
}
```

### 5. CloudWatch log group

```bash
aws logs create-log-group --log-group-name /ecs/network-buoy
```

---

## task-definition.json

Edit these placeholders before deploying:

| Placeholder    | Replace with                                      |
|----------------|---------------------------------------------------|
| `ACCOUNT_ID`   | Your 12-digit AWS account ID                      |
| `REGION`       | e.g. `us-east-1`                                  |
| `fs-XXXXXXXX`  | EFS FileSystemId from step 3                      |

---

## Deploy

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
export ECS_CLUSTER=network-buoy
export ECS_SERVICE=network-buoy

./deploy.sh
```

The script:
1. Authenticates Docker to ECR
2. Builds and pushes the image (tagged with current git SHA + `latest`)
3. Registers a new task definition revision
4. Updates the ECS service to the new revision (rolling deploy, zero downtime)

---

## Security group

The task's security group needs inbound TCP open on all honeypot ports from `0.0.0.0/0` — that's the point. Outbound only needs HTTPS (443) for ECR pulls and SSM.

```bash
# Example — adjust sg-xxxxxxxx to your security group
for port in 21 22 23 25 80 110 143 389 443 445 3306 3389 5432 6379 6443 8080 9090 9200 27017; do
  aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port $port \
    --cidr 0.0.0.0/0
done
```

---

## Reading logs

Logs stream to CloudWatch and persist on EFS. To tail live from CloudWatch:

```bash
aws logs tail /ecs/network-buoy --follow --format short
```

To filter credential captures only:

```bash
aws logs filter-log-events \
  --log-group-name /ecs/network-buoy \
  --filter-pattern '"event":"credential"'
```

---

## Notes

- First boot pulls `gemma3:1b` (~800 MB). The task will be slow to become healthy until the model is cached. EFS persists the ollama model volume so subsequent deploys are instant.
- CPU: 2 vCPU is the minimum for comfortable CPU inference with gemma3:1b. Drop to 1 vCPU if cost matters — it'll be slower but functional.
- The task uses `awsvpc` networking — assign it a public subnet + public IP, or put a NAT gateway in front.
