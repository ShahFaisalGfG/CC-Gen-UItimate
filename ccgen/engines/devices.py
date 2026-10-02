# devices.py - choose the accelerator torch and ONNX Runtime models run on
#
# Speech engines use two runtimes. PyTorch (XTTS) reaches NVIDIA through CUDA, AMD through ROCm
# builds (which also report as CUDA), Intel through XPU builds, Apple Silicon through MPS, and
# any DirectX 12 GPU on Windows through torch-directml when it is installed. ONNX Runtime (Piper
# and Kokoro) reaches NVIDIA through CUDA, AMD through ROCm, any DirectX 12 GPU through DirectML,
# and Apple Silicon through CoreML. Which of these exist depends on the installed build, so every
# choice is probed at run time and the CPU is always the last resort.

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

from ccgen.config.defaults import DubbingDefaults

_log = logging.getLogger(__name__)

DEVICE_AUTO = DubbingDefaults.DEVICE_AUTO
DEVICE_CPU = DubbingDefaults.DEVICE_CPU

_T = TypeVar("_T")

# Preference order for ONNX Runtime; whichever the installed onnxruntime build offers is used.
_ONNX_GPU_PROVIDERS = (
    ("CUDAExecutionProvider", "NVIDIA GPU (CUDA)"),
    ("ROCMExecutionProvider", "AMD GPU (ROCm)"),
    ("DmlExecutionProvider", "GPU (DirectML)"),
    ("CoreMLExecutionProvider", "Apple GPU (Core ML)"),
)
_ONNX_CPU = "CPUExecutionProvider"
# The device each probed model ran fastest on, by model file and device setting. Hardware doesn't
# change while the app runs, so later jobs open the model there directly: opening a session can
# take seconds, and probing opens one per device.
_fastest_onnx: dict[tuple[str, str], str] = {}


@dataclass(frozen=True)
class Accelerator:
    """One device a model can run on: a runtime-specific handle and a label for the user."""

    handle: Any
    label: str

    @property
    def is_gpu(self) -> bool:
        """True for anything other than the CPU."""
        return self.label != "CPU"


def torch_accelerators(preference: str = DEVICE_AUTO) -> list[Accelerator]:
    """Return torch devices to try in order, ending with the CPU."""
    import torch

    cpu = Accelerator(torch.device("cpu"), "CPU")
    if preference == DEVICE_CPU:
        return [cpu]
    found: list[Accelerator] = []
    try:
        if torch.cuda.is_available():
            # ROCm builds of torch report AMD GPUs through the CUDA API and set torch.version.hip.
            hip = getattr(getattr(torch, "version", None), "hip", None)
            vendor = "AMD GPU (ROCm)" if hip else "NVIDIA GPU (CUDA)"
            found.append(Accelerator(torch.device("cuda"), f"{vendor}: {torch.cuda.get_device_name(0)}"))
        xpu = getattr(torch, "xpu", None)
        if xpu is not None and xpu.is_available():
            found.append(Accelerator(torch.device("xpu"), f"Intel GPU (XPU): {xpu.get_device_name(0)}"))
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            found.append(Accelerator(torch.device("mps"), "Apple GPU (Metal)"))
    except Exception:
        _log.warning("Probing torch GPU support failed", exc_info=True)
    try:
        import torch_directml  # type: ignore[import-not-found]

        if torch_directml.is_available():
            found.append(Accelerator(torch_directml.device(), f"GPU (DirectML): {torch_directml.device_name(0)}"))
    except ImportError:
        pass
    except Exception:
        _log.warning("Probing DirectML for torch failed", exc_info=True)
    return found + [cpu]


def onnx_accelerators(preference: str = DEVICE_AUTO) -> list[Accelerator]:
    """Return ONNX Runtime provider lists to try in order, ending with the CPU alone."""
    import onnxruntime

    cpu = Accelerator([_ONNX_CPU], "CPU")
    if preference == DEVICE_CPU:
        return [cpu]
    available = set(onnxruntime.get_available_providers())
    found = [
        Accelerator([provider, _ONNX_CPU], label)
        for provider, label in _ONNX_GPU_PROVIDERS
        if provider in available
    ]
    return found + [cpu]


def onnx_session(
    model_path: str,
    preference: str = DEVICE_AUTO,
    probe: Optional[Callable[[Any], None]] = None,
) -> tuple[Any, Accelerator]:
    """Open an ONNX Runtime session on the fastest device that can run the model.

    With a `probe` (a short sample run), every candidate is timed and the quickest kept: small
    speech models often run slower on an integrated GPU than on the CPU, and a GPU provider can
    accept a model yet fail on its first run (DirectML on older Intel graphics rejects some of
    Kokoro's layers). Without one, the first device that opens the model is used. A probed
    choice is remembered for the rest of the session, with the CPU still behind a GPU choice.
    """
    import onnxruntime

    def open_session(accelerator: Accelerator) -> Any:
        options = onnxruntime.SessionOptions()
        if "DmlExecutionProvider" in accelerator.handle:
            # DirectML does not support memory patterns or parallel execution.
            options.enable_mem_pattern = False
            options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
        return onnxruntime.InferenceSession(model_path, sess_options=options, providers=accelerator.handle)

    accelerators = onnx_accelerators(preference)
    key = (model_path, preference)
    known = [a for a in accelerators if a.label == _fastest_onnx.get(key)]
    if known:
        return first_working(known + accelerators[-1:] if known[0].is_gpu else known, open_session)
    if probe is None or len(accelerators) == 1:
        return first_working(accelerators, open_session)
    session, accelerator = fastest_working(accelerators, open_session, probe)
    _fastest_onnx[key] = accelerator.label
    return session, accelerator


def fastest_working(
    accelerators: list[Accelerator],
    load: Callable[[Accelerator], _T],
    probe: Callable[[_T], None],
) -> tuple[_T, Accelerator]:
    """Load on every accelerator, time `probe` on each, and keep the fastest that works.

    The probe runs twice per device and only the second run is timed, so one-time warm-up
    (graph compilation, GPU memory allocation) doesn't count against a device.
    """
    timed: list[tuple[float, _T, Accelerator]] = []
    for accelerator in accelerators:
        try:
            value = load(accelerator)
            probe(value)
            start = time.perf_counter()
            probe(value)
            timed.append((time.perf_counter() - start, value, accelerator))
        except Exception as e:
            if not accelerator.is_gpu:
                raise
            _log.warning("%s failed, trying the next device: %r", accelerator.label, e)
    seconds, value, accelerator = min(timed, key=lambda entry: entry[0])
    _log.info(
        "Running on %s (%s)", accelerator.label,
        ", ".join(f"{a.label}: {s * 1000:.0f} ms" for s, _, a in timed),
    )
    return value, accelerator


def first_working(
    accelerators: list[Accelerator],
    load: Callable[[Accelerator], _T],
) -> tuple[_T, Accelerator]:
    """Load on each accelerator in turn and return the first that works.

    A GPU whose driver or memory can't take the model falls back to the next device, and
    finally the CPU, so a broken accelerator slows a job down instead of failing it.
    """
    error: Optional[Exception] = None
    for accelerator in accelerators:
        try:
            value = load(accelerator)
            _log.info("Running on %s", accelerator.label)
            return value, accelerator
        except Exception as e:
            if not accelerator.is_gpu:
                raise
            _log.warning("%s failed, trying the next device: %r", accelerator.label, e)
            error = e
    raise RuntimeError(f"No device could load the model: {error}")


def describe_accelerators() -> dict[str, list[str]]:
    """Labels of every device each runtime can use, for the self-test and logs."""
    result: dict[str, list[str]] = {}
    for runtime, probe in (("torch", torch_accelerators), ("onnxruntime", onnx_accelerators)):
        try:
            result[runtime] = [a.label for a in probe()]
        except ImportError as e:
            result[runtime] = [f"unavailable ({e})"]
    return result
