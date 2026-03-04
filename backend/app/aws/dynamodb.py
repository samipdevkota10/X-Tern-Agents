"""
DynamoDB client for case storage.
"""
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class DynamoDBClient:
    """Client for DynamoDB operations."""

    def __init__(self):
        """Initialize DynamoDB client."""
        self._client = None
        self._table = None

    @property
    def client(self):
        """Get or create DynamoDB client."""
        if self._client is None:
            kwargs = {
                "region_name": settings.AWS_REGION,
            }
            if settings.DYNAMODB_ENDPOINT_URL:
                kwargs["endpoint_url"] = settings.DYNAMODB_ENDPOINT_URL
            if settings.AWS_ACCESS_KEY_ID:
                kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            self._client = boto3.resource("dynamodb", **kwargs)
        return self._client

    @property
    def table(self):
        """Get the cases table."""
        if self._table is None:
            self._table = self.client.Table(settings.DYNAMODB_TABLE_CASES)
        return self._table

    async def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Put an item into DynamoDB.
        
        Args:
            item: The item to store.
            
        Returns:
            The stored item.
        """
        try:
            self.table.put_item(Item=item)
            logger.info("Item stored in DynamoDB", item_id=item.get("id"))
            return item
        except ClientError as e:
            logger.error("Failed to store item in DynamoDB", error=str(e))
            raise

    async def get_item(self, key: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Get an item from DynamoDB.
        
        Args:
            key: The key to look up.
            
        Returns:
            The item if found, None otherwise.
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error("Failed to get item from DynamoDB", error=str(e))
            raise

    async def scan(self, filter_expression: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Scan the table for items.
        
        Args:
            filter_expression: Optional filter expression.
            
        Returns:
            List of items.
        """
        try:
            if filter_expression:
                response = self.table.scan(FilterExpression=filter_expression)
            else:
                response = self.table.scan()
            return response.get("Items", [])
        except ClientError as e:
            logger.error("Failed to scan DynamoDB", error=str(e))
            raise

    async def update_item(
        self,
        key: dict[str, Any],
        update_expression: str,
        expression_values: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an item in DynamoDB.
        
        Args:
            key: The key of the item to update.
            update_expression: The update expression.
            expression_values: The expression attribute values.
            
        Returns:
            The updated item.
        """
        try:
            response = self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW",
            )
            logger.info("Item updated in DynamoDB", item_key=key)
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error("Failed to update item in DynamoDB", error=str(e))
            raise


# Singleton instance
dynamodb_client = DynamoDBClient()
