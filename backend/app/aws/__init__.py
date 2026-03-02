"""AWS client modules"""
from app.aws.dynamodb import DynamoDBClient
from app.aws.s3 import S3Client
from app.aws.bedrock import BedrockClient

__all__ = ["DynamoDBClient", "S3Client", "BedrockClient"]
