import os
import logging
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional

logger = logging.getLogger(__name__)
CACHE_DIR = os.getenv("DATASETS_DIR", "./datasets")

class S3ImageHandler:
    @staticmethod
    def list_s3_images(s3_path: str) -> List[str]:
        valid_ext = ('.jpg','.jpeg','.png','.bmp','.tiff','.tif')
        path = s3_path[5:]
        bucket, prefix = (path.split('/',1)+[''])[:2]
        s3 = boto3.client('s3')
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            logger.error(f"Bucket not found: {bucket}")
            return []
        paginator = s3.get_paginator('list_objects_v2')
        keys=[]
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents',[]):
                key=obj['Key']
                if key.lower().endswith(valid_ext):
                    keys.append(key)
        return [f"s3://{bucket}/{k}" for k in keys]

    @staticmethod
    def get_local_image_path(image_path: str) -> str:
        if not image_path.startswith('s3://'):
            return image_path
        bucket,key = image_path[5:].split('/',1)
        local=os.path.join(CACHE_DIR,bucket,key)
        if os.path.exists(local):
            logger.info(f"[CACHE] hit: {local}")
            return local
        os.makedirs(os.path.dirname(local),exist_ok=True)
        logger.info(f"[CACHE] download: {image_path} -> {local}")
        boto3.client('s3').download_file(bucket,key,local)
        return local

    @staticmethod
    def download_s3_folder(s3_path: str, local_dir: Optional[str]=None) -> None:
        valid_ext = ('.jpg','.jpeg','.png','.bmp','.tiff','.tif')
        path=s3_path[5:]
        bucket,prefix=(path.split('/',1)+[''])[:2]
        if not local_dir:
            local_dir=os.path.join(CACHE_DIR,bucket,prefix)
        os.makedirs(local_dir,exist_ok=True)
        logger.info(f"[CACHE] Download S3 folder: {s3_path} -> {local_dir}")
        s3=boto3.client('s3')
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            logger.error(f"Bucket not found: {bucket}")
            return
        paginator=s3.get_paginator('list_objects_v2')
        keys=[]
        for page in paginator.paginate(Bucket=bucket,Prefix=prefix):
            for obj in page.get('Contents',[]):
                key=obj['Key']
                if key.lower().endswith(valid_ext):
                    keys.append(key)
        logger.info(f"[CACHE] Found {len(keys)} image keys in {s3_path}")
        def dl(k):
            rel=k[len(prefix):].lstrip('/')
            out=os.path.join(local_dir,rel)
            if os.path.exists(out):
                logger.info(f"[CACHE] hit (skip): {out}")
                return
            os.makedirs(os.path.dirname(out),exist_ok=True)
            logger.info(f"[CACHE] download: s3://{bucket}/{k} -> {out}")
            s3.download_file(bucket,k,out)
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(dl,keys))
        logger.info(f"[CACHE] Folder download complete: {len(keys)} files")
