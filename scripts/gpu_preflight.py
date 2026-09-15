"""Confere se o ambiente uv está pronto para treinamento local em GPU."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import bitsandbytes
import torch


MINIMUM_VRAM_BYTES = 7 * 1024**3


def main() -> None:
    report: dict[str, object] = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "bitsandbytes_version": bitsandbytes.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        device = torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(device)
        free_bytes, total_bytes = torch.cuda.mem_get_info(device)
        report.update(
            {
                "device_name": properties.name,
                "compute_capability": f"{properties.major}.{properties.minor}",
                "total_vram_gib": round(total_bytes / 1024**3, 2),
                "free_vram_gib": round(free_bytes / 1024**3, 2),
                "bf16_supported": torch.cuda.is_bf16_supported(),
                "meets_minimum_vram": total_bytes >= MINIMUM_VRAM_BYTES,
            }
        )
    report_path = Path(__file__).resolve().parents[1] / "artifacts" / "reports" / "gpu-preflight.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["cuda_available"]:
        raise SystemExit("CUDA não está disponível para PyTorch.")
    if not report["meets_minimum_vram"]:
        raise SystemExit("A GPU não tem a VRAM mínima de 7 GiB para este plano.")


if __name__ == "__main__":
    main()
