"""
Model Optimization Module for MT Service

Provides ONNX and TensorRT optimization for MarianMT models
to achieve the 20-80ms latency requirements.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import torch
import numpy as np
from transformers import MarianMTModel, MarianTokenizer
import onnx
import onnxruntime as ort

try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    TRT_AVAILABLE = True
except ImportError:
    TRT_AVAILABLE = False
    logging.warning("TensorRT not available - falling back to ONNX optimization only")

logger = logging.getLogger(__name__)

class ModelOptimizer:
    """Handles model optimization and conversion"""
    
    def __init__(self, cache_dir: str = "/app/models/optimized"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.onnx_providers = self._get_onnx_providers()
        
    def _get_onnx_providers(self) -> List[str]:
        """Get available ONNX Runtime providers in priority order"""
        available_providers = ort.get_available_providers()
        
        # Priority order: CUDA, TensorRT, CPU
        preferred_providers = [
            'TensorrtExecutionProvider',
            'CUDAExecutionProvider', 
            'CPUExecutionProvider'
        ]
        
        providers = []
        for provider in preferred_providers:
            if provider in available_providers:
                providers.append(provider)
                
        logger.info(f"Available ONNX providers: {providers}")
        return providers
    
    def optimize_model(
        self, 
        model_name: str, 
        source_lang: str, 
        target_lang: str
    ) -> Tuple[Any, MarianTokenizer, str]:
        """Optimize a model for inference"""
        pair_key = f"{source_lang}-{target_lang}"
        
        # Check if optimized model already exists
        onnx_path = self.cache_dir / f"{pair_key}.onnx"
        trt_path = self.cache_dir / f"{pair_key}.trt"
        
        # Load tokenizer
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        
        # Try TensorRT first (if available and model exists)
        if TRT_AVAILABLE and trt_path.exists():
            try:
                logger.info(f"Loading TensorRT model for {pair_key}")
                trt_model = self._load_tensorrt_model(trt_path)
                return trt_model, tokenizer, "tensorrt"
            except Exception as e:
                logger.warning(f"Failed to load TensorRT model: {e}")
        
        # Try ONNX model
        if onnx_path.exists():
            try:
                logger.info(f"Loading ONNX model for {pair_key}")
                onnx_session = ort.InferenceSession(
                    str(onnx_path), 
                    providers=self.onnx_providers
                )
                return onnx_session, tokenizer, "onnx"
            except Exception as e:
                logger.warning(f"Failed to load ONNX model: {e}")
        
        # Convert and optimize if needed
        logger.info(f"Converting model {model_name} to optimized format")
        
        # Load original PyTorch model
        pytorch_model = MarianMTModel.from_pretrained(model_name)
        
        # Convert to ONNX
        onnx_session = self._convert_to_onnx(
            pytorch_model, tokenizer, onnx_path, pair_key
        )
        
        # Try to convert to TensorRT if available
        if TRT_AVAILABLE and torch.cuda.is_available():
            try:
                trt_model = self._convert_to_tensorrt(onnx_path, trt_path, pair_key)
                if trt_model:
                    return trt_model, tokenizer, "tensorrt"
            except Exception as e:
                logger.warning(f"TensorRT conversion failed: {e}")
        
        return onnx_session, tokenizer, "onnx"
    
    def _convert_to_onnx(
        self, 
        model: MarianMTModel, 
        tokenizer: MarianTokenizer,
        output_path: Path,
        pair_key: str
    ) -> ort.InferenceSession:
        """Convert PyTorch model to ONNX"""
        logger.info(f"Converting {pair_key} model to ONNX")
        
        # Set model to evaluation mode
        model.eval()
        
        # Create dummy input
        dummy_text = "Hello, this is a test sentence for model conversion."
        inputs = tokenizer(dummy_text, return_tensors="pt", padding=True)
        
        # Export to ONNX
        torch.onnx.export(
            model,
            (inputs.input_ids, inputs.attention_mask),
            str(output_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence"},
                "attention_mask": {0: "batch_size", 1: "sequence"},
                "logits": {0: "batch_size", 1: "sequence"}
            },
            export_params=True,
            opset_version=11
        )
        
        # Optimize ONNX model
        self._optimize_onnx_model(output_path)
        
        # Create inference session
        session = ort.InferenceSession(
            str(output_path),
            providers=self.onnx_providers
        )
        
        logger.info(f"Successfully converted {pair_key} to ONNX")
        return session
    
    def _optimize_onnx_model(self, model_path: Path):
        """Apply ONNX optimizations"""
        try:
            import onnxoptimizer
            
            # Load and optimize
            onnx_model = onnx.load(str(model_path))
            optimized_model = onnxoptimizer.optimize(
                onnx_model,
                ["eliminate_deadend", "eliminate_identity", 
                 "eliminate_nop_dropout", "eliminate_nop_transpose",
                 "fuse_consecutive_transposes", "fuse_transpose_into_gemm"]
            )
            
            # Save optimized model
            onnx.save(optimized_model, str(model_path))
            logger.info("Applied ONNX optimizations")
            
        except ImportError:
            logger.warning("onnxoptimizer not available - skipping optimizations")
        except Exception as e:
            logger.warning(f"ONNX optimization failed: {e}")
    
    def _convert_to_tensorrt(
        self, 
        onnx_path: Path, 
        trt_path: Path, 
        pair_key: str
    ) -> Optional['TRTInferenceWrapper']:
        """Convert ONNX model to TensorRT"""
        if not TRT_AVAILABLE:
            return None
            
        logger.info(f"Converting {pair_key} to TensorRT")
        
        try:
            # Create TensorRT builder
            builder = trt.Builder(trt.Logger(trt.Logger.WARNING))
            config = builder.create_builder_config()
            
            # Set optimization parameters
            config.max_workspace_size = 1 << 28  # 256MB
            config.set_flag(trt.BuilderFlag.FP16)  # Enable FP16 precision
            
            # Parse ONNX model
            network = builder.create_network(
                1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            )
            parser = trt.OnnxParser(network, trt.Logger(trt.Logger.WARNING))
            
            with open(onnx_path, 'rb') as f:
                if not parser.parse(f.read()):
                    logger.error("Failed to parse ONNX model")
                    return None
            
            # Build TensorRT engine
            engine = builder.build_engine(network, config)
            if not engine:
                logger.error("Failed to build TensorRT engine")
                return None
            
            # Serialize and save engine
            with open(trt_path, 'wb') as f:
                f.write(engine.serialize())
            
            logger.info(f"Successfully converted {pair_key} to TensorRT")
            return TRTInferenceWrapper(engine)
            
        except Exception as e:
            logger.error(f"TensorRT conversion failed: {e}")
            return None
    
    def _load_tensorrt_model(self, trt_path: Path) -> 'TRTInferenceWrapper':
        """Load existing TensorRT model"""
        runtime = trt.Runtime(trt.Logger(trt.Logger.WARNING))
        
        with open(trt_path, 'rb') as f:
            engine = runtime.deserialize_cuda_engine(f.read())
            
        return TRTInferenceWrapper(engine)

class TRTInferenceWrapper:
    """Wrapper for TensorRT inference"""
    
    def __init__(self, engine):
        self.engine = engine
        self.context = engine.create_execution_context()
        self.stream = cuda.Stream()
        
        # Allocate buffers
        self.inputs = []
        self.outputs = []
        self.bindings = []
        
        for binding in engine:
            size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if engine.binding_is_input(binding):
                self.inputs.append({'host': host_mem, 'device': device_mem})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem})
    
    def infer(self, input_data: Dict[str, np.ndarray]) -> np.ndarray:
        """Run inference with TensorRT"""
        # Copy input data to device
        for i, data in enumerate(input_data.values()):
            np.copyto(self.inputs[i]['host'], data.ravel())
            cuda.memcpy_htod_async(
                self.inputs[i]['device'], 
                self.inputs[i]['host'], 
                self.stream
            )
        
        # Run inference
        self.context.execute_async_v2(
            bindings=self.bindings, 
            stream_handle=self.stream.handle
        )
        
        # Copy outputs back to host
        for output in self.outputs:
            cuda.memcpy_dtoh_async(
                output['host'], 
                output['device'], 
                self.stream
            )
        
        # Synchronize stream
        self.stream.synchronize()
        
        return self.outputs[0]['host']

class OptimizedTranslationEngine:
    """Translation engine using optimized models"""
    
    def __init__(self, optimizer: ModelOptimizer):
        self.optimizer = optimizer
        self.models: Dict[Tuple[str, str], Any] = {}
        self.tokenizers: Dict[Tuple[str, str], MarianTokenizer] = {}
        self.model_types: Dict[Tuple[str, str], str] = {}
        
    def load_model(self, model_name: str, source_lang: str, target_lang: str):
        """Load and optimize model"""
        pair_key = (source_lang, target_lang)
        
        if pair_key in self.models:
            return  # Already loaded
            
        start_time = time.time()
        model, tokenizer, model_type = self.optimizer.optimize_model(
            model_name, source_lang, target_lang
        )
        
        self.models[pair_key] = model
        self.tokenizers[pair_key] = tokenizer
        self.model_types[pair_key] = model_type
        
        load_time = time.time() - start_time
        logger.info(
            f"Loaded optimized {model_type} model for {source_lang}→{target_lang} "
            f"in {load_time:.2f}s"
        )
    
    def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Tuple[str, float]:
        """Translate text using optimized model"""
        pair_key = (source_lang, target_lang)
        
        if pair_key not in self.models:
            raise ValueError(f"Model not loaded for {source_lang}→{target_lang}")
        
        model = self.models[pair_key]
        tokenizer = self.tokenizers[pair_key]
        model_type = self.model_types[pair_key]
        
        start_time = time.time()
        
        # Tokenize input
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        
        # Run inference based on model type
        if model_type == "tensorrt":
            output = self._infer_tensorrt(model, inputs)
        elif model_type == "onnx":
            output = self._infer_onnx(model, inputs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Decode output
        translation = tokenizer.decode(output, skip_special_tokens=True)
        
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return translation, inference_time
    
    def _infer_onnx(
        self, 
        session: ort.InferenceSession, 
        inputs: Dict[str, torch.Tensor]
    ) -> List[int]:
        """Run inference with ONNX model"""
        ort_inputs = {
            "input_ids": inputs.input_ids.numpy(),
            "attention_mask": inputs.attention_mask.numpy()
        }
        
        outputs = session.run(None, ort_inputs)
        logits = outputs[0]
        
        # Get predicted token IDs
        predicted_ids = np.argmax(logits, axis=-1)
        return predicted_ids[0].tolist()
    
    def _infer_tensorrt(
        self, 
        wrapper: TRTInferenceWrapper, 
        inputs: Dict[str, torch.Tensor]
    ) -> List[int]:
        """Run inference with TensorRT model"""
        input_data = {
            "input_ids": inputs.input_ids.numpy(),
            "attention_mask": inputs.attention_mask.numpy()
        }
        
        output = wrapper.infer(input_data)
        logits = output.reshape(-1, tokenizer.vocab_size)  # Reshape as needed
        
        # Get predicted token IDs
        predicted_ids = np.argmax(logits, axis=-1)
        return predicted_ids.tolist()

def benchmark_optimization():
    """Benchmark optimization performance"""
    optimizer = ModelOptimizer()
    engine = OptimizedTranslationEngine(optimizer)
    
    # Test model
    model_name = "Helsinki-NLP/opus-mt-en-es"
    engine.load_model(model_name, "en", "es")
    
    test_sentences = [
        "Hello, how are you?",
        "The weather is beautiful today.",
        "I would like to make a reservation.",
        "Technology is advancing rapidly.",
        "Please help me with this problem."
    ]
    
    results = []
    for sentence in test_sentences:
        translation, latency = engine.translate(sentence, "en", "es")
        results.append({
            "input": sentence,
            "output": translation,
            "latency_ms": latency
        })
        print(f"'{sentence}' → '{translation}' ({latency:.1f}ms)")
    
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    print(f"\nAverage latency: {avg_latency:.1f}ms")
    
    return results

if __name__ == "__main__":
    # Run benchmark
    benchmark_optimization()