import os
import yaml
import logging
import time
import itertools
import concurrent.futures
import traceback
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .core.structure import StructureManager
from .core.stats import StatsCollector
from .core.config import config

from .core.datasets.imagenet import generate_imagenet_tree
from .core.datasets.coco import generate_coco_hierarchy
from .core.datasets.openimages import generate_openimages_hierarchy
from .core.datasets.tencent import generate_tencent_hierarchy

logger = logging.getLogger(__name__)

@dataclass
class JobConfig:
    name: str
    dataset: str
    params: Dict[str, Any]
    output_path: str
    analyze: bool = False

class BatchProcessor:
    def __init__(self, manifest_path: str, workers: int = 1):
        self.manifest_path = manifest_path
        self.workers = workers
        self.base_dir = os.path.dirname(os.path.abspath(manifest_path))
        self.jobs: List[JobConfig] = []
        self.global_config = {}
        self._load_manifest()

    def _load_manifest(self):
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        self.global_config = data.get('config', {})
        output_root = self.global_config.get('output_dir', 'output')
        if not os.path.isabs(output_root):
            output_root = os.path.normpath(os.path.join(self.base_dir, output_root))
        for j in data.get('jobs', []):
            self.jobs.append(self._parse_job_entry(j, output_root))
        matrix = data.get('matrix', None)
        if matrix:
            self.jobs.extend(self._expand_matrix(matrix, output_root))
            
    def _parse_job_entry(self, entry: Dict, output_root: str) -> JobConfig:
        name = entry.get('name', 'unnamed')
        dataset = entry.get('dataset', self.global_config.get('dataset', 'tencent'))
        params = self.global_config.get('default_params', {}).copy()
        params.update(entry.get('params', {}))
        filename = entry.get('output_filename')
        if not filename:
            filename = f"{dataset}_{name}.yaml".replace(" ", "_").lower()
        out_path = os.path.join(output_root, filename)
        return JobConfig(name=name, dataset=dataset, params=params, output_path=out_path, analyze=entry.get('analyze', self.global_config.get('analyze', False)))

    def _expand_matrix(self, matrix: Dict, output_root: str) -> List[JobConfig]:
        base_params = matrix.get('base_params', {})
        axes = matrix.get('axes', {})
        keys = sorted(axes.keys())
        values_list = [axes[k] for k in keys]
        expanded_jobs = []
        for combination in itertools.product(*values_list):
            combo_params = dict(zip(keys, combination))
            final_params = base_params.copy()
            final_params.update(combo_params)
            name_parts = ["matrix"]
            for k, v in combo_params.items():
                short_k = k.replace("min_", "").replace("semantic_", "")
                name_parts.append(f"{short_k}{v}")
            job_name = "_".join(name_parts)
            dataset = matrix.get('dataset', self.global_config.get('dataset', 'tencent'))
            filename = f"{dataset}_{job_name}.yaml"
            out_path = os.path.join(output_root, filename)
            expanded_jobs.append(JobConfig(name=job_name, dataset=dataset, params=final_params, output_path=out_path, analyze=matrix.get('analyze', self.global_config.get('analyze', False))))
        return expanded_jobs

    def run(self):
        logger.info(f"Starting batch execution: {len(self.jobs)} jobs with {self.workers} workers.")
        for job in self.jobs:
            os.makedirs(os.path.dirname(job.output_path), exist_ok=True)
        results = []
        if self.workers > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
                future_to_job = {executor.submit(run_single_job, job): job for job in self.jobs}
                for future in concurrent.futures.as_completed(future_to_job):
                    job = future_to_job[future]
                    try:
                        result = future.result()
                        results.append(result)
                        status = "✅" if result['success'] else "❌"
                        print(f"{status} Job '{job.name}' finished ({result['duration']:.1f}s)")
                    except Exception as e:
                        print(f"❌ Job '{job.name}' crashed: {e}")
                        results.append({"name": job.name, "success": False, "error": str(e)})
        else:
            for job in self.jobs:
                print(f"▶ Running '{job.name}'...")
                res = run_single_job(job)
                results.append(res)
                status = "✅" if res['success'] else "❌"
                print(f"{status} Finished ({res['duration']:.1f}s)")
        self._generate_report(results)

    def _generate_report(self, results: List[Dict]):
        output_root = self.global_config.get('output_dir', 'output')
        if not os.path.isabs(output_root):
            output_root = os.path.normpath(os.path.join(self.base_dir, output_root))
        report_path = os.path.join(output_root, "batch_report.md")
        mgr = StructureManager()
        def count_nodes(data):
            if isinstance(data, dict):
                count = 1
                for v in data.values():
                    count += count_nodes(v)
                return count
            return 1
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Batch Execution Report\n\n")
            f.write("| Job | Dataset | Nodes | Leaves | Duration | Status |\n")
            f.write("|---|---|---|---|---|---|")
            for res in results:
                if not res.get('success'):
                    f.write(f"| {res['name']} | - | - | - | - | ❌ {res.get('error')} |\n")
                    continue
                nodes, leaves = 0, 0
                job_obj = next((j for j in self.jobs if j.name == res['name']), None)
                if job_obj and os.path.exists(job_obj.output_path):
                    try:
                        data = mgr.load_structure(job_obj.output_path)
                        nodes = count_nodes(data)
                        leaves = len(mgr.extract_terms(data))
                    except: pass
                dur = f"{res['duration']:.1f}s"
                f.write(f"| {res['name']} | {res['dataset']} | {nodes} | {leaves} | {dur} | ✅ |\n")
        print(f"\n📄 Report generated at {report_path}")

def run_single_job(job: JobConfig) -> Dict:
    start_time = time.time()
    try:
        stats = StatsCollector()
        stats.set_metadata("job_name", job.name)
        stats.set_metadata("dataset", job.dataset)
        p = job.params
        hierarchy = None
        if job.dataset == 'tencent':
            hierarchy = generate_tencent_hierarchy(max_depth=p.get('depth', 10), with_glosses=not p.get('no_glosses', False), smart=p.get('smart', False), min_significance_depth=p.get('min_depth', 6), min_hyponyms=p.get('min_hyponyms', 10), min_leaf_size=p.get('min_leaf_size', 5), merge_orphans=p.get('merge_orphans', False), semantic_cleanup=p.get('semantic_clean', False), semantic_threshold=p.get('semantic_threshold', 0.1), semantic_arrangement=p.get('semantic_arrange', False), semantic_arrangement_threshold=p.get('semantic_arrange_threshold', 0.15), semantic_arrangement_min_cluster=p.get('semantic_arrange_min_cluster', 5), stats=stats, preview_limit=p.get('preview_limit'), smart_overrides=p.get('smart_overrides', None))
        elif job.dataset == 'imagenet':
            hierarchy = generate_imagenet_tree(root_synset_str=p.get('root', 'entity.n.01'), max_depth=p.get('depth', 10), smart=p.get('smart', False), min_significance_depth=p.get('min_depth', 6), min_hyponyms=p.get('min_hyponyms', 10), min_leaf_size=p.get('min_leaf_size', 5), merge_orphans=p.get('merge_orphans', False), semantic_cleanup=p.get('semantic_clean', False), semantic_threshold=p.get('semantic_threshold', 0.1), preview_limit=p.get('preview_limit'), stats=stats)
        elif job.dataset == 'openimages':
             hierarchy = generate_openimages_hierarchy(max_depth=p.get('depth', 10), smart=p.get('smart', False), bbox_only=p.get('bbox_only', False), min_significance_depth=p.get('min_depth', 6), min_hyponyms=p.get('min_hyponyms', 10), min_leaf_size=p.get('min_leaf_size', 5), merge_orphans=p.get('merge_orphans', False), semantic_cleanup=p.get('semantic_clean', False), preview_limit=p.get('preview_limit'), stats=stats)
        else:
            raise ValueError(f"Unknown dataset: {job.dataset}")
        mgr = StructureManager()
        mgr.save_structure(hierarchy, job.output_path)
        if config.get("generation.save_stats", True):
            base, _ = os.path.splitext(job.output_path)
            stats.save_to_json(f"{base}.stats.json")
        return {"name": job.name, "dataset": job.dataset, "success": True, "duration": time.time() - start_time, "stats": stats.to_dict()}
    except Exception as e:
        logger.error(f"Job {job.name} failed: {e}")
        traceback.print_exc()
        return {"name": job.name, "dataset": job.dataset, "success": False, "duration": time.time() - start_time, "error": str(e)}
