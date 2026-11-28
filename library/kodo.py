"""Qiniu KODO's authenticated S3 endpoint. Browser uploads are scoped to individual parts."""
from functools import lru_cache
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings


@lru_cache(maxsize=1)
def client():
    return boto3.client(
        's3', region_name=settings.KODO_REGION,
        endpoint_url=f'https://s3.{settings.KODO_REGION}.qiniucs.com',
        aws_access_key_id=settings.KODO_ACCESS_KEY, aws_secret_access_key=settings.KODO_SECRET_KEY,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'},
                      request_checksum_calculation='when_required',
                      response_checksum_validation='when_required'),
    )


def address(key):
    return {'Bucket': settings.KODO_BUCKET, 'Key': key}


def download_url(key, name):
    params = address(key)
    params['ResponseContentDisposition'] = "attachment; filename*=UTF-8''" + quote(name, safe='')
    return client().generate_presigned_url('get_object', Params=params, ExpiresIn=60)


def part_size(size):
    # The S3 protocol permits at most 10,000 parts.
    return max(8 * 1024 * 1024, (size + 9999) // 10000)


def start(payload):
    if not payload['size']:
        return ''
    created = client().create_multipart_upload(**address(payload['key']), ContentType='application/octet-stream')
    return created['UploadId']


def part_url(payload, number):
    if number < 1 or (number - 1) * part_size(payload['size']) >= payload['size']:
        raise ValueError('Invalid upload part')
    params = dict(address(payload['key']), UploadId=payload['upload_id'], PartNumber=number)
    return client().generate_presigned_url('upload_part', Params=params, ExpiresIn=900)


def finish(payload):
    obj = address(payload['key'])
    if not payload['size']:
        client().put_object(**obj, Body=b'')
        return
    transfer = dict(obj, UploadId=payload['upload_id'])
    try:
        parts = []
        total = 0
        pages = client().get_paginator('list_parts').paginate(**transfer)
        for page in pages:
            for part in page.get('Parts', []):
                number = part['PartNumber']
                size = part['Size']
                if number != len(parts) + 1 or size != min(part_size(payload['size']), payload['size'] - total):
                    raise ValueError('Incomplete upload')
                parts.append({'PartNumber': number, 'ETag': part['ETag']})
                total += size
        if total != payload['size']:
            raise ValueError('Incomplete upload')
        client().complete_multipart_upload(**transfer, MultipartUpload={'Parts': parts})
    except ClientError as exc:
        # A previous completion may have succeeded before the metadata transaction committed.
        if exc.response['Error']['Code'] != 'NoSuchUpload':
            raise
    if client().head_object(**obj)['ContentLength'] != payload['size']:
        raise ValueError('Stored length differs')
