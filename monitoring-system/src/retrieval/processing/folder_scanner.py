import os
import logging
from typing import List
from ..utils.s3_handler import S3ImageHandler, CACHE_DIR

logger=logging.getLogger(__name__)

class FolderScanner(S3ImageHandler):
    valid_extensions = ('.jpg','.jpeg','.png','.bmp','.tiff','.tif')
    def __init__(self, cleaner=None):
        self.cleaner=cleaner

    def scan_folder(self, folder_path: str, resize:int=1024) -> List[str]:
        logger.info(f"[scan_folder] Начало сканирования: {folder_path}")
        images:List[str]=[]
        if folder_path.startswith('s3://'):
            self.download_s3_folder(folder_path)
            path=folder_path[5:]
            bucket,prefix=(path.split('/',1)+[''])[:2]
            root=os.path.join(CACHE_DIR,bucket,prefix)
            logger.info(f"[scan_folder] Local cache root: {root}")
            for r,_,fs in os.walk(root):
                imgs=[os.path.join(r,f) for f in fs if f.lower().endswith(self.valid_extensions)]
                if not imgs: continue
                if self.cleaner and len(imgs)>1:
                    logger.info(f"[scan_folder] Running cleaner on {r}")
                    filtered=self.cleaner.process_folder(r,resize=resize)
                    logger.info(f"[scan_folder] Filtered: {len(filtered)} in {r}")
                    images.extend(filtered)
                else:
                    images.extend(imgs)
        else:
            from pathlib import Path
            p=Path(folder_path)
            if not p.is_dir():
                logger.error(f"[scan_folder] Directory not found: {folder_path}")
                raise ValueError(f"Directory not found: {folder_path}")
            for r,_,fs in os.walk(folder_path):
                imgs=[os.path.join(r,f) for f in fs if f.lower().endswith(self.valid_extensions)]
                if not imgs: continue
                if self.cleaner and len(imgs)>1:
                    logger.info(f"[scan_folder] Running cleaner on {r}")
                    filtered=self.cleaner.process_folder(r,resize=resize)
                    logger.info(f"[scan_folder] Filtered: {len(filtered)} in {r}")
                    images.extend(filtered)
                else:
                    images.extend(imgs)
        images.sort()
        logger.info(f"[scan_folder] Final list ({len(images)}): {images[:5]} …")
        return images
