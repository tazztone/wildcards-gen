"""
Download utilities for external datasets.

Handles downloading and caching of:
- COCO annotations
- Open Images hierarchy and class descriptions
- ImageNet class lists (1k and 21k)
- Tencent ML-Images hierarchy
"""

import os
import logging
import urllib.request
import zipfile
import requests
from typing import Tuple
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Default downloads directory (relative to package root)
DOWNLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "downloads"
)


class DownloadProgressBar(tqdm):
    """Progress bar for urllib downloads."""
    
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url: str, dest_path: str, force: bool = False) -> None:
    """Download a file from URL to destination path."""
    if os.path.exists(dest_path) and not force:
        logger.debug(f"File already exists: {dest_path}")
        return

    logger.info(f"Downloading {url}...")
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with DownloadProgressBar(
            unit='B', unit_scale=True, miniters=1,
            desc=url.split('/')[-1]
        ) as t:
            urllib.request.urlretrieve(url, filename=dest_path, reporthook=t.update_to)
        logger.info(f"Downloaded to {dest_path}")
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        raise


def unzip_file(zip_path: str, extract_to: str) -> None:
    """Extract a zip file."""
    logger.info(f"Extracting {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info("Extraction complete.")
    except Exception as e:
        logger.error(f"Failed to unzip {zip_path}: {e}")
        raise


def ensure_coco_data(data_dir: str = None) -> str:
    """
    Ensure COCO annotations are present.
    
    Returns:
        Path to instances_train2017.json
    """
    data_dir = data_dir or DOWNLOADS_DIR
    zip_name = "annotations_trainval2017.zip"
    zip_path = os.path.join(data_dir, zip_name)
    json_path = os.path.join(data_dir, "annotations", "instances_train2017.json")
    url = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"

    if os.path.exists(json_path):
        return json_path

    if not os.path.exists(zip_path):
        download_file(url, zip_path)

    unzip_file(zip_path, data_dir)

    # Clean up zip
    try:
        os.remove(zip_path)
    except Exception as e:
        logger.warning(f"Could not delete {zip_path}: {e}")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Expected {json_path} after extraction")

    return json_path


def ensure_openimages_data(data_dir: str = None) -> Tuple[str, str]:
    """
    Ensure Open Images hierarchy and class descriptions are present.
    
    Returns:
        Tuple of (hierarchy_path, classes_path)
    """
    data_dir = data_dir or DOWNLOADS_DIR
    
    hierarchy_url = "https://storage.googleapis.com/openimages/2018_04/bbox_labels_600_hierarchy.json"
    classes_url = "https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions.csv"

    hierarchy_path = os.path.join(data_dir, "bbox_labels_600_hierarchy.json")
    classes_path = os.path.join(data_dir, "oidv7-class-descriptions.csv")

    download_file(hierarchy_url, hierarchy_path)
    download_file(classes_url, classes_path)

    return hierarchy_path, classes_path


def ensure_imagenet_1k_data(data_dir: str = None) -> str:
    """
    Ensure ImageNet 1k class list is present.
    
    Returns:
        Path to imagenet_class_index.json
    """
    data_dir = data_dir or DOWNLOADS_DIR
    url = "https://raw.githubusercontent.com/raghakot/keras-vis/master/resources/imagenet_class_index.json"
    path = os.path.join(data_dir, "imagenet_class_index.json")

    download_file(url, path)
    return path


def ensure_imagenet_21k_data(data_dir: str = None) -> Tuple[str, str]:
    """
    Ensure ImageNet 21k ID list and lemmas are present.
    
    Returns:
        Tuple of (ids_path, lemmas_path)
    """
    data_dir = data_dir or DOWNLOADS_DIR
    
    ids_url = "https://storage.googleapis.com/bit_models/imagenet21k_wordnet_ids.txt"
    lemmas_url = "https://storage.googleapis.com/bit_models/imagenet21k_wordnet_lemmas.txt"

    ids_path = os.path.join(data_dir, "imagenet21k_wordnet_ids.txt")
    lemmas_path = os.path.join(data_dir, "imagenet21k_wordnet_lemmas.txt")

    download_file(ids_url, ids_path)
    download_file(lemmas_url, lemmas_path)

    return ids_path, lemmas_path


def download_tencent_hierarchy(data_dir: str = None) -> str:
    """
    Download Tencent ML-Images hierarchy file.
    
    Returns:
        Path to hierarchy.txt
    """
    data_dir = data_dir or DOWNLOADS_DIR
    os.makedirs(data_dir, exist_ok=True)
    
    url = "https://raw.githubusercontent.com/Tencent/tencent-ml-images/master/data/dictionary_and_semantic_hierarchy.txt"
    target_path = os.path.join(data_dir, "tencent_hierarchy.txt")
    
    if os.path.exists(target_path):
        return target_path
        
    logger.info(f"Downloading Tencent hierarchy from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    
    with open(target_path, 'wb') as f, tqdm(
        total=total_size, unit='iB', unit_scale=True
    ) as pbar:
        for data in response.iter_content(block_size):
            size = f.write(data)
            pbar.update(size)
            
    return target_path
