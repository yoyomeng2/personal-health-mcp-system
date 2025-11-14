#!/bin/bash
set -euo pipefail

############################################
# Bootstrap AWS resources for GitHub Actions OIDC access
############################################fd

############################################
# 0. Auth and Setup
############################################
aws sso login --profile ${AWS_PROFILE}

if [ -z "${REPO_OWNER:-}" ] || [ -z "${REPO_NAME:-}" ] || [ -z "${BRANCH_NAME:-}" ]; then
  echo "Error: REPO_OWNER, REPO_NAME, and BRANCH_NAME environment variables must be set."
  exit 1
fi

# Create local IAM user for AssumeRole testing if not present
LOCAL_TEST_USER="local-terraform-tester"
LOCAL_TEST_USER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:user/${LOCAL_TEST_USER}"
if aws iam get-user --user-name "$LOCAL_TEST_USER" >/dev/null 2>&1; then
  echo "IAM user $LOCAL_TEST_USER already exists."
else
  echo "Creating IAM user $LOCAL_TEST_USER for local testing..."
  aws iam create-user --user-name "$LOCAL_TEST_USER"
  # Attach minimal policy for AssumeRole
  aws iam attach-user-policy --user-name "$LOCAL_TEST_USER" --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
  echo "IAM user $LOCAL_TEST_USER created and policy attached."
fi
echo "Local test IAM user ARN: $LOCAL_TEST_USER_ARN"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region --profile ${AWS_PROFILE})
AWS_ASSUMED_ROLE_NAME=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)

OIDC_URL="https://token.actions.githubusercontent.com"
GITHUB_OIDC_THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"
OIDC_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

ROLE_NAME="github-actions-role"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

#############################################
# 1. Ensure OIDC provider exists
#############################################
echo "Ensuring OIDC provider exists..."

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" >/dev/null 2>&1; then
    echo "OIDC provider already exists: $OIDC_ARN"
else
    echo "Creating OIDC provider..."
    aws iam create-open-id-connect-provider \
        --url "$OIDC_URL" \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list "$GITHUB_OIDC_THUMBPRINT"
    echo "OIDC provider created."
fi


#############################################
# 2. Create trust policy file
#############################################
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:${REPO_OWNER}/${REPO_NAME}:ref:refs/heads/${BRANCH_NAME}"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${AWS_ACCOUNT_ID}:user/local-terraform-tester"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF


#############################################
# 3. Ensure IAM role exists
#############################################
echo "Ensuring IAM role exists..."

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    echo "Role already exists: $ROLE_NAME"
else
    echo "Creating IAM role..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json
    echo "Role created."
fi


#############################################
# 4. Ensure policies are attached
#############################################
echo "Ensuring policies are attached..."

POLICIES=(
  "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
  "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
)

for POLICY_ARN in "${POLICIES[@]}"; do
    if aws iam list-attached-role-policies --role-name "$ROLE_NAME" \
        | grep -q "$POLICY_ARN"; then
        echo "Policy already attached: $POLICY_ARN"
    else
        echo "Attaching policy: $POLICY_ARN"
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "$POLICY_ARN"
    fi
done


#############################################
# 5. Ensure S3 bucket exists
#############################################
echo "Ensuring S3 bucket exists..."

if aws s3api head-bucket --bucket "$AWS_TF_BUCKET_NAME" >/dev/null 2>&1; then
    echo "S3 bucket already exists: $AWS_TF_BUCKET_NAME"
else
    echo "Creating S3 bucket..."
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$AWS_TF_BUCKET_NAME"
    else
        aws s3api create-bucket \
            --bucket "$AWS_TF_BUCKET_NAME" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    echo "Bucket created."
fi


#############################################
# 6. Cleanup and Output
#############################################
rm -f /tmp/trust-policy.json
echo "Role ARN: $ROLE_ARN"
