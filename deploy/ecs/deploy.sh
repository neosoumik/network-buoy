#!/usr/bin/env bash
# Deploy network-buoy to ECS Fargate.
# Usage: ./deploy.sh [REGION] [ACCOUNT_ID] [CLUSTER] [SERVICE]
# Defaults to env vars if set.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
CLUSTER="${ECS_CLUSTER:-network-buoy}"
SERVICE="${ECS_SERVICE:-network-buoy}"
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/network-buoy"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

echo "==> Logging into ECR"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_REPO"

echo "==> Building image"
docker build -t "$ECR_REPO:$IMAGE_TAG" -t "$ECR_REPO:latest" buoy/

echo "==> Pushing image"
docker push "$ECR_REPO:$IMAGE_TAG"
docker push "$ECR_REPO:latest"

echo "==> Registering task definition"
# Substitute placeholders
TASK_DEF=$(sed \
  -e "s/ACCOUNT_ID/$ACCOUNT_ID/g" \
  -e "s/REGION/$REGION/g" \
  deploy/ecs/task-definition.json)

TASK_ARN=$(echo "$TASK_DEF" \
  | aws ecs register-task-definition \
      --cli-input-json /dev/stdin \
      --query "taskDefinition.taskDefinitionArn" \
      --output text)

echo "==> Registered: $TASK_ARN"

echo "==> Updating service $SERVICE in cluster $CLUSTER"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$TASK_ARN" \
  --force-new-deployment \
  --query "service.deployments[0].status" \
  --output text

echo "==> Done. Monitor with:"
echo "    aws ecs describe-services --cluster $CLUSTER --services $SERVICE"
