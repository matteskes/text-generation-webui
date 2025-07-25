<<<<<<< Updated upstream
# Text generation web UI

A Gradio web UI for Large Language Models.

Its goal is to become the [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) of text generation.

[Try the Deep Reason extension](https://oobabooga.gumroad.com/l/deep_reason)

|![Image1](https://github.com/oobabooga/screenshots/raw/main/INSTRUCT-3.5.png) | ![Image2](https://github.com/oobabooga/screenshots/raw/main/CHAT-3.5.png) |
|:---:|:---:|
|![Image1](https://github.com/oobabooga/screenshots/raw/main/DEFAULT-3.5.png) | ![Image2](https://github.com/oobabooga/screenshots/raw/main/PARAMETERS-3.5.png) |

## Features

- Supports multiple local text generation backends, including [llama.cpp](https://github.com/ggerganov/llama.cpp), [Transformers](https://github.com/huggingface/transformers), [ExLlamaV3](https://github.com/turboderp-org/exllamav3), [ExLlamaV2](https://github.com/turboderp-org/exllamav2), and [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) (the latter via its own [Dockerfile](https://github.com/oobabooga/text-generation-webui/blob/main/docker/TensorRT-LLM/Dockerfile)).
- Easy setup: Choose between **portable builds** (zero setup, just unzip and run) for GGUF models on Windows/Linux/macOS, or the one-click installer that creates a self-contained `installer_files` directory.
- 100% offline and private, with zero telemetry, external resources, or remote update requests.
- **File attachments**: Upload text files, PDF documents, and .docx documents to talk about their contents.
- **Web search**: Optionally search the internet with LLM-generated queries to add context to the conversation.
- Aesthetic UI with dark and light themes.
- Syntax highlighting for code blocks and LaTeX rendering for mathematical expressions.
- `instruct` mode for instruction-following (like ChatGPT), and `chat-instruct`/`chat` modes for talking to custom characters.
- Automatic prompt formatting using Jinja2 templates. You don't need to ever worry about prompt formats.
- Edit messages, navigate between message versions, and branch conversations at any point.
- Multiple sampling parameters and generation options for sophisticated text generation control.
- Switch between different models in the UI without restarting.
- Automatic GPU layers for GGUF models (on NVIDIA GPUs).
- Free-form text generation in the Notebook tab without being limited to chat turns.
- OpenAI-compatible API with Chat and Completions endpoints, including tool-calling support – see [examples](https://github.com/oobabooga/text-generation-webui/wiki/12-%E2%80%90-OpenAI-API#examples).
- Extension support, with numerous built-in and user-contributed extensions available. See the [wiki](https://github.com/oobabooga/text-generation-webui/wiki/07-%E2%80%90-Extensions) and [extensions directory](https://github.com/oobabooga/text-generation-webui-extensions) for details.

## How to install

#### Option 1: Portable builds (get started in 1 minute)

No installation needed – just download, unzip and run. All dependencies included.

Compatible with GGUF (llama.cpp) models on Windows, Linux, and macOS.

Download from here: https://github.com/oobabooga/text-generation-webui/releases

#### Option 2: One-click installer

For users who need additional backends (ExLlamaV3, Transformers) or extensions (TTS, voice input, translation, etc). Requires ~10GB disk space and downloads PyTorch.

1. Clone the repository, or [download its source code](https://github.com/oobabooga/text-generation-webui/archive/refs/heads/main.zip) and extract it.
2. Run the startup script for your OS: `start_windows.bat`, `start_linux.sh`, or `start_macos.sh`.
3. When prompted, select your GPU vendor.
4. After installation, open `http://127.0.0.1:7860` in your browser.

To restart the web UI later, run the same `start_` script.

To reinstall with a fresh Python environment, delete the `installer_files` folder and run the `start_` script again.

You can pass command-line flags directly (e.g., `./start_linux.sh --help`), or add them to `user_data/CMD_FLAGS.txt` (e.g., `--api` to enable the API).

To update, run the update script for your OS: `update_wizard_windows.bat`, `update_wizard_linux.sh`, or `update_wizard_macos.sh`.

<details>
<summary>
One-click installer details
</summary>

### One-click-installer

The script uses Miniforge to set up a Conda environment in the `installer_files` folder.

If you ever need to install something manually in the `installer_files` environment, you can launch an interactive shell using the cmd script: `cmd_linux.sh`, `cmd_windows.bat`, or `cmd_macos.sh`.

* There is no need to run any of those scripts (`start_`, `update_wizard_`, or `cmd_`) as admin/root.
* To install requirements for extensions, it is recommended to use the update wizard script with the "Install/update extensions requirements" option. At the end, this script will install the main requirements for the project to make sure that they take precedence in case of version conflicts.
* For automated installation, you can use the `GPU_CHOICE`, `LAUNCH_AFTER_INSTALL`, and `INSTALL_EXTENSIONS` environment variables. For instance: `GPU_CHOICE=A LAUNCH_AFTER_INSTALL=FALSE INSTALL_EXTENSIONS=TRUE ./start_linux.sh`.

</details>

<details>
<summary>
Manual portable installation with venv
</summary>

### Manual portable installation with venv

Very fast setup that should work on any Python 3.9+:

```bash
# Clone repository
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies (choose appropriate file under requirements/portable for your hardware)
pip install -r requirements/portable/requirements.txt

# Launch server (basic command)
python server.py --portable --api --auto-launch

# When done working, deactivate
deactivate
```
</details>

<details>
<summary>
Manual full installation with conda or docker
</summary>

### Full installation with Conda

#### 0. Install Conda

https://github.com/conda-forge/miniforge

On Linux or WSL, Miniforge can be automatically installed with these two commands:

```
curl -sL "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh" > "Miniforge3.sh"
bash Miniforge3.sh
```

For other platforms, download from: https://github.com/conda-forge/miniforge/releases/latest

#### 1. Create a new conda environment

```
conda create -n textgen python=3.11
conda activate textgen
```

#### 2. Install Pytorch

| System | GPU | Command |
|--------|---------|---------|
| Linux/WSL | NVIDIA | `pip3 install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124` |
| Linux/WSL | CPU only | `pip3 install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu` |
| Linux | AMD | `pip3 install torch==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.2.4` |
| MacOS + MPS | Any | `pip3 install torch==2.6.0` |
| Windows | NVIDIA | `pip3 install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124` |
| Windows | CPU only | `pip3 install torch==2.6.0` |

The up-to-date commands can be found here: https://pytorch.org/get-started/locally/.

If you need `nvcc` to compile some library manually, you will additionally need to install this:

```
conda install -y -c "nvidia/label/cuda-12.4.1" cuda
```

#### 3. Install the web UI

```
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui
pip install -r <requirements file according to table below>
```

Requirements file to use:

| GPU | CPU | requirements file to use |
|--------|---------|---------|
| NVIDIA | has AVX2 | `requirements.txt` |
| NVIDIA | no AVX2 | `requirements_noavx2.txt` |
| AMD | has AVX2 | `requirements_amd.txt` |
| AMD | no AVX2 | `requirements_amd_noavx2.txt` |
| CPU only | has AVX2 | `requirements_cpu_only.txt` |
| CPU only | no AVX2 | `requirements_cpu_only_noavx2.txt` |
| Apple | Intel | `requirements_apple_intel.txt` |
| Apple | Apple Silicon | `requirements_apple_silicon.txt` |

### Start the web UI

```
conda activate textgen
cd text-generation-webui
python server.py
```

Then browse to

`http://127.0.0.1:7860`

#### Manual install

The `requirements*.txt` above contain various wheels precompiled through GitHub Actions. If you wish to compile things manually, or if you need to because no suitable wheels are available for your hardware, you can use `requirements_nowheels.txt` and then install your desired loaders manually.

### Alternative: Docker

```
For NVIDIA GPU:
ln -s docker/{nvidia/Dockerfile,nvidia/docker-compose.yml,.dockerignore} .
For AMD GPU:
ln -s docker/{amd/Dockerfile,amd/docker-compose.yml,.dockerignore} .
For Intel GPU:
ln -s docker/{intel/Dockerfile,amd/docker-compose.yml,.dockerignore} .
For CPU only
ln -s docker/{cpu/Dockerfile,cpu/docker-compose.yml,.dockerignore} .
cp docker/.env.example .env
#Create logs/cache dir :
mkdir -p user_data/logs user_data/cache
# Edit .env and set:
#   TORCH_CUDA_ARCH_LIST based on your GPU model
#   APP_RUNTIME_GID      your host user's group id (run `id -g` in a terminal)
#   BUILD_EXTENIONS      optionally add comma separated list of extensions to build
# Edit user_data/CMD_FLAGS.txt and add in it the options you want to execute (like --listen --cpu)
#
docker compose up --build
```

* You need to have Docker Compose v2.17 or higher installed. See [this guide](https://github.com/oobabooga/text-generation-webui/wiki/09-%E2%80%90-Docker) for instructions.
* For additional docker files, check out [this repository](https://github.com/Atinoda/text-generation-webui-docker).

### Updating the requirements

From time to time, the `requirements*.txt` change. To update, use these commands:

```
conda activate textgen
cd text-generation-webui
pip install -r <requirements file that you have used> --upgrade
```
</details>

<details>
<summary>
List of command-line flags
</summary>

```txt
usage: server.py [-h] [--multi-user] [--model MODEL] [--lora LORA [LORA ...]] [--model-dir MODEL_DIR] [--lora-dir LORA_DIR] [--model-menu] [--settings SETTINGS]
                 [--extensions EXTENSIONS [EXTENSIONS ...]] [--verbose] [--idle-timeout IDLE_TIMEOUT] [--loader LOADER] [--cpu] [--cpu-memory CPU_MEMORY] [--disk] [--disk-cache-dir DISK_CACHE_DIR]
                 [--load-in-8bit] [--bf16] [--no-cache] [--trust-remote-code] [--force-safetensors] [--no_use_fast] [--attn-implementation IMPLEMENTATION] [--load-in-4bit] [--use_double_quant]
                 [--compute_dtype COMPUTE_DTYPE] [--quant_type QUANT_TYPE] [--flash-attn] [--threads THREADS] [--threads-batch THREADS_BATCH] [--batch-size BATCH_SIZE] [--no-mmap] [--mlock]
                 [--gpu-layers N] [--tensor-split TENSOR_SPLIT] [--numa] [--no-kv-offload] [--row-split] [--extra-flags EXTRA_FLAGS] [--streaming-llm] [--ctx-size N] [--cache-type N]
                 [--model-draft MODEL_DRAFT] [--draft-max DRAFT_MAX] [--gpu-layers-draft GPU_LAYERS_DRAFT] [--device-draft DEVICE_DRAFT] [--ctx-size-draft CTX_SIZE_DRAFT] [--gpu-split GPU_SPLIT]
                 [--autosplit] [--cfg-cache] [--no_flash_attn] [--no_xformers] [--no_sdpa] [--num_experts_per_token N] [--enable_tp] [--cpp-runner] [--deepspeed] [--nvme-offload-dir NVME_OFFLOAD_DIR]
                 [--local_rank LOCAL_RANK] [--alpha_value ALPHA_VALUE] [--rope_freq_base ROPE_FREQ_BASE] [--compress_pos_emb COMPRESS_POS_EMB] [--listen] [--listen-port LISTEN_PORT]
                 [--listen-host LISTEN_HOST] [--share] [--auto-launch] [--gradio-auth GRADIO_AUTH] [--gradio-auth-path GRADIO_AUTH_PATH] [--ssl-keyfile SSL_KEYFILE] [--ssl-certfile SSL_CERTFILE]
                 [--subpath SUBPATH] [--old-colors] [--portable] [--api] [--public-api] [--public-api-id PUBLIC_API_ID] [--api-port API_PORT] [--api-key API_KEY] [--admin-key ADMIN_KEY]
                 [--api-enable-ipv6] [--api-disable-ipv4] [--nowebui]

Text generation web UI

options:
  -h, --help                                show this help message and exit

Basic settings:
  --multi-user                              Multi-user mode. Chat histories are not saved or automatically loaded. Warning: this is likely not safe for sharing publicly.
  --model MODEL                             Name of the model to load by default.
  --lora LORA [LORA ...]                    The list of LoRAs to load. If you want to load more than one LoRA, write the names separated by spaces.
  --model-dir MODEL_DIR                     Path to directory with all the models.
  --lora-dir LORA_DIR                       Path to directory with all the loras.
  --model-menu                              Show a model menu in the terminal when the web UI is first launched.
  --settings SETTINGS                       Load the default interface settings from this yaml file. See user_data/settings-template.yaml for an example. If you create a file called
                                            user_data/settings.yaml, this file will be loaded by default without the need to use the --settings flag.
  --extensions EXTENSIONS [EXTENSIONS ...]  The list of extensions to load. If you want to load more than one extension, write the names separated by spaces.
  --verbose                                 Print the prompts to the terminal.
  --idle-timeout IDLE_TIMEOUT               Unload model after this many minutes of inactivity. It will be automatically reloaded when you try to use it again.

Model loader:
  --loader LOADER                           Choose the model loader manually, otherwise, it will get autodetected. Valid options: Transformers, llama.cpp, ExLlamav3_HF, ExLlamav2_HF, ExLlamav2,
                                            TensorRT-LLM.

Transformers/Accelerate:
  --cpu                                     Use the CPU to generate text. Warning: Training on CPU is extremely slow.
  --cpu-memory CPU_MEMORY                   Maximum CPU memory in GiB. Use this for CPU offloading.
  --disk                                    If the model is too large for your GPU(s) and CPU combined, send the remaining layers to the disk.
  --disk-cache-dir DISK_CACHE_DIR           Directory to save the disk cache to. Defaults to "user_data/cache".
  --load-in-8bit                            Load the model with 8-bit precision (using bitsandbytes).
  --bf16                                    Load the model with bfloat16 precision. Requires NVIDIA Ampere GPU.
  --no-cache                                Set use_cache to False while generating text. This reduces VRAM usage slightly, but it comes at a performance cost.
  --trust-remote-code                       Set trust_remote_code=True while loading the model. Necessary for some models.
  --force-safetensors                       Set use_safetensors=True while loading the model. This prevents arbitrary code execution.
  --no_use_fast                             Set use_fast=False while loading the tokenizer (it's True by default). Use this if you have any problems related to use_fast.
  --attn-implementation IMPLEMENTATION      Attention implementation. Valid options: sdpa, eager, flash_attention_2.

bitsandbytes 4-bit:
  --load-in-4bit                            Load the model with 4-bit precision (using bitsandbytes).
  --use_double_quant                        use_double_quant for 4-bit.
  --compute_dtype COMPUTE_DTYPE             compute dtype for 4-bit. Valid options: bfloat16, float16, float32.
  --quant_type QUANT_TYPE                   quant_type for 4-bit. Valid options: nf4, fp4.

llama.cpp:
  --flash-attn                              Use flash-attention.
  --threads THREADS                         Number of threads to use.
  --threads-batch THREADS_BATCH             Number of threads to use for batches/prompt processing.
  --batch-size BATCH_SIZE                   Maximum number of prompt tokens to batch together when calling llama_eval.
  --no-mmap                                 Prevent mmap from being used.
  --mlock                                   Force the system to keep the model in RAM.
  --gpu-layers N, --n-gpu-layers N          Number of layers to offload to the GPU.
  --tensor-split TENSOR_SPLIT               Split the model across multiple GPUs. Comma-separated list of proportions. Example: 60,40.
  --numa                                    Activate NUMA task allocation for llama.cpp.
  --no-kv-offload                           Do not offload the K, Q, V to the GPU. This saves VRAM but reduces the performance.
  --row-split                               Split the model by rows across GPUs. This may improve multi-gpu performance.
  --extra-flags EXTRA_FLAGS                 Extra flags to pass to llama-server. Format: "flag1=value1,flag2,flag3=value3". Example: "override-tensor=exps=CPU"
  --streaming-llm                           Activate StreamingLLM to avoid re-evaluating the entire prompt when old messages are removed.

Context and cache:
  --ctx-size N, --n_ctx N, --max_seq_len N  Context size in tokens.
  --cache-type N, --cache_type N            KV cache type; valid options: llama.cpp - fp16, q8_0, q4_0; ExLlamaV2 - fp16, fp8, q8, q6, q4; ExLlamaV3 - fp16, q2 to q8 (can specify k_bits and v_bits
                                            separately, e.g. q4_q8).

Speculative decoding:
  --model-draft MODEL_DRAFT                 Path to the draft model for speculative decoding.
  --draft-max DRAFT_MAX                     Number of tokens to draft for speculative decoding.
  --gpu-layers-draft GPU_LAYERS_DRAFT       Number of layers to offload to the GPU for the draft model.
  --device-draft DEVICE_DRAFT               Comma-separated list of devices to use for offloading the draft model. Example: CUDA0,CUDA1
  --ctx-size-draft CTX_SIZE_DRAFT           Size of the prompt context for the draft model. If 0, uses the same as the main model.

ExLlamaV2:
  --gpu-split GPU_SPLIT                     Comma-separated list of VRAM (in GB) to use per GPU device for model layers. Example: 20,7,7.
  --autosplit                               Autosplit the model tensors across the available GPUs. This causes --gpu-split to be ignored.
  --cfg-cache                               ExLlamav2_HF: Create an additional cache for CFG negative prompts. Necessary to use CFG with that loader.
  --no_flash_attn                           Force flash-attention to not be used.
  --no_xformers                             Force xformers to not be used.
  --no_sdpa                                 Force Torch SDPA to not be used.
  --num_experts_per_token N                 Number of experts to use for generation. Applies to MoE models like Mixtral.
  --enable_tp                               Enable Tensor Parallelism (TP) in ExLlamaV2.

TensorRT-LLM:
  --cpp-runner                              Use the ModelRunnerCpp runner, which is faster than the default ModelRunner but doesn't support streaming yet.

DeepSpeed:
  --deepspeed                               Enable the use of DeepSpeed ZeRO-3 for inference via the Transformers integration.
  --nvme-offload-dir NVME_OFFLOAD_DIR       DeepSpeed: Directory to use for ZeRO-3 NVME offloading.
  --local_rank LOCAL_RANK                   DeepSpeed: Optional argument for distributed setups.

RoPE:
  --alpha_value ALPHA_VALUE                 Positional embeddings alpha factor for NTK RoPE scaling. Use either this or compress_pos_emb, not both.
  --rope_freq_base ROPE_FREQ_BASE           If greater than 0, will be used instead of alpha_value. Those two are related by rope_freq_base = 10000 * alpha_value ^ (64 / 63).
  --compress_pos_emb COMPRESS_POS_EMB       Positional embeddings compression factor. Should be set to (context length) / (model's original context length). Equal to 1/rope_freq_scale.

Gradio:
  --listen                                  Make the web UI reachable from your local network.
  --listen-port LISTEN_PORT                 The listening port that the server will use.
  --listen-host LISTEN_HOST                 The hostname that the server will use.
  --share                                   Create a public URL. This is useful for running the web UI on Google Colab or similar.
  --auto-launch                             Open the web UI in the default browser upon launch.
  --gradio-auth GRADIO_AUTH                 Set Gradio authentication password in the format "username:password". Multiple credentials can also be supplied with "u1:p1,u2:p2,u3:p3".
  --gradio-auth-path GRADIO_AUTH_PATH       Set the Gradio authentication file path. The file should contain one or more user:password pairs in the same format as above.
  --ssl-keyfile SSL_KEYFILE                 The path to the SSL certificate key file.
  --ssl-certfile SSL_CERTFILE               The path to the SSL certificate cert file.
  --subpath SUBPATH                         Customize the subpath for gradio, use with reverse proxy
  --old-colors                              Use the legacy Gradio colors, before the December/2024 update.
  --portable                                Hide features not available in portable mode like training.

API:
  --api                                     Enable the API extension.
  --public-api                              Create a public URL for the API using Cloudfare.
  --public-api-id PUBLIC_API_ID             Tunnel ID for named Cloudflare Tunnel. Use together with public-api option.
  --api-port API_PORT                       The listening port for the API.
  --api-key API_KEY                         API authentication key.
  --admin-key ADMIN_KEY                     API authentication key for admin tasks like loading and unloading models. If not set, will be the same as --api-key.
  --api-enable-ipv6                         Enable IPv6 for the API
  --api-disable-ipv4                        Disable IPv4 for the API
  --nowebui                                 Do not launch the Gradio UI. Useful for launching the API in standalone mode.
```

</details>

## Downloading models

Models should be placed in the folder `text-generation-webui/user_data/models`. They are usually downloaded from [Hugging Face](https://huggingface.co/models?pipeline_tag=text-generation&sort=downloads&search=gguf).

To check if a GGUF model will fit in your hardware before downloading it, you can use this tool I created:

[Accurate GGUF VRAM Calculator](https://huggingface.co/spaces/oobabooga/accurate-gguf-vram-calculator)

* GGUF models are a single file and should be placed directly into `user_data/models`. Example:

```
text-generation-webui
└── user_data
    └── models
        └── llama-2-13b-chat.Q4_K_M.gguf
```

* The remaining model types (like 16-bit Transformers models and EXL2 models) are made of several files and must be placed in a subfolder. Example:

```
text-generation-webui
└── user_data
    └── models
        └── lmsys_vicuna-33b-v1.3
            ├── config.json
            ├── generation_config.json
            ├── pytorch_model-00001-of-00007.bin
            ├── pytorch_model-00002-of-00007.bin
            ├── pytorch_model-00003-of-00007.bin
            ├── pytorch_model-00004-of-00007.bin
            ├── pytorch_model-00005-of-00007.bin
            ├── pytorch_model-00006-of-00007.bin
            ├── pytorch_model-00007-of-00007.bin
            ├── pytorch_model.bin.index.json
            ├── special_tokens_map.json
            ├── tokenizer_config.json
            └── tokenizer.model
```

In both cases, you can use the "Model" tab of the UI to download the model from Hugging Face automatically. It is also possible to download it via the command-line with:

```
python download-model.py organization/model
```

Run `python download-model.py --help` to see all the options.

## Documentation

https://github.com/oobabooga/text-generation-webui/wiki

## Google Colab notebook

https://colab.research.google.com/github/oobabooga/text-generation-webui/blob/main/Colab-TextGen-GPU.ipynb

## Community

https://www.reddit.com/r/Oobabooga/

## Acknowledgment

In August 2023, [Andreessen Horowitz](https://a16z.com/) (a16z) provided a generous grant to encourage and support my independent work on this project. I am **extremely** grateful for their trust and recognition.
=======
# Text generation web UI

A gradio web UI for running Large Language Models like LLaMA, llama.cpp, GPT-J, OPT, and GALACTICA.

Its goal is to become the [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) of text generation.

|![Image1](https://github.com/oobabooga/screenshots/raw/main/qa.png) | ![Image2](https://github.com/oobabooga/screenshots/raw/main/cai3.png) |
|:---:|:---:|
|![Image3](https://github.com/oobabooga/screenshots/raw/main/gpt4chan.png) | ![Image4](https://github.com/oobabooga/screenshots/raw/main/galactica.png) |

## Features

* 3 interface modes: default, notebook, and chat
* Multiple model backends: transformers, llama.cpp, ExLlama, AutoGPTQ, GPTQ-for-LLaMa
* Dropdown menu for quickly switching between different models
* LoRA: load and unload LoRAs on the fly, train a new LoRA
* Precise instruction templates for chat mode, including Llama 2, Alpaca, Vicuna, WizardLM, StableLM, and many others
* [Multimodal pipelines, including LLaVA and MiniGPT-4](https://github.com/oobabooga/text-generation-webui/tree/main/extensions/multimodal)
* 8-bit and 4-bit inference through bitsandbytes
* CPU mode for transformers models
* [DeepSpeed ZeRO-3 inference](docs/DeepSpeed.md)
* [Extensions](docs/Extensions.md)
* [Custom chat characters](docs/Chat-mode.md)
* Very efficient text streaming
* Markdown output with LaTeX rendering, to use for instance with [GALACTICA](https://github.com/paperswithcode/galai)
* Nice HTML output for GPT-4chan
* API, including endpoints for websocket streaming ([see the examples](https://github.com/oobabooga/text-generation-webui/blob/main/api-examples))

To learn how to use the various features, check out the Documentation: https://github.com/oobabooga/text-generation-webui/tree/main/docs

## Installation

### One-click installers

| Windows | Linux | macOS | WSL |
|--------|--------|--------|--------|
| [oobabooga-windows.zip](https://github.com/oobabooga/text-generation-webui/releases/download/installers/oobabooga_windows.zip) | [oobabooga-linux.zip](https://github.com/oobabooga/text-generation-webui/releases/download/installers/oobabooga_linux.zip) |[oobabooga-macos.zip](https://github.com/oobabooga/text-generation-webui/releases/download/installers/oobabooga_macos.zip) | [oobabooga-wsl.zip](https://github.com/oobabooga/text-generation-webui/releases/download/installers/oobabooga_wsl.zip) |

Just download the zip above, extract it, and double-click on "start". The web UI and all its dependencies will be installed in the same folder.

* The source codes are here: https://github.com/oobabooga/one-click-installers
* There is no need to run the installers as admin.
* AMD doesn't work on Windows.
* Huge thanks to [@jllllll](https://github.com/jllllll), [@ClayShoaf](https://github.com/ClayShoaf), and [@xNul](https://github.com/xNul) for their contributions to these installers.

### Manual installation using Conda

Recommended if you have some experience with the command line.

#### 0. Install Conda

https://docs.conda.io/en/latest/miniconda.html

On Linux or WSL, it can be automatically installed with these two commands:

```
curl -sL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" > "Miniconda3.sh"
bash Miniconda3.sh
```
Source: https://educe-ubc.github.io/conda.html

#### 1. Create a new conda environment

```
conda create -n textgen python=3.10.9
conda activate textgen
```

#### 2. Install Pytorch

| System | GPU | Command |
|--------|---------|---------|
| Linux/WSL | NVIDIA | `pip3 install torch torchvision torchaudio` |
| Linux/WSL | CPU only | `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu` |
| Linux | AMD | `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.4.2` |
| MacOS + MPS | Any | `pip3 install torch torchvision torchaudio` |
| Windows | NVIDIA | `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117` |
| Windows | CPU only | `pip3 install torch torchvision torchaudio` |

The up-to-date commands can be found here: https://pytorch.org/get-started/locally/. 

#### 2.1 Special instructions

* MacOS users: https://github.com/oobabooga/text-generation-webui/pull/393
* AMD users: https://rentry.org/eq3hg

#### 3. Install the web UI

```
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui
pip install -r requirements.txt
```

#### bitsandbytes

bitsandbytes >= 0.39 may not work on older NVIDIA GPUs. In that case, to use `--load-in-8bit`, you may have to downgrade like this:

* Linux: `pip install bitsandbytes==0.38.1`
* Windows: `pip install https://github.com/jllllll/bitsandbytes-windows-webui/raw/main/bitsandbytes-0.38.1-py3-none-any.whl`

### Alternative: Docker

```
ln -s docker/{Dockerfile,docker-compose.yml,.dockerignore} .
cp docker/.env.example .env
# Edit .env and set TORCH_CUDA_ARCH_LIST based on your GPU model
docker compose up --build
```

* You need to have docker compose v2.17 or higher installed. See [this guide](https://github.com/oobabooga/text-generation-webui/blob/main/docs/Docker.md) for instructions.
* For additional docker files, check out [this repository](https://github.com/Atinoda/text-generation-webui-docker).

### Updating the requirements

From time to time, the `requirements.txt` changes. To update, use this command:

```
conda activate textgen
cd text-generation-webui
pip install -r requirements.txt --upgrade
```
## Downloading models

Models should be placed inside the `models/` folder.

[Hugging Face](https://huggingface.co/models?pipeline_tag=text-generation&sort=downloads) is the main place to download models. These are some examples:

* [Pythia](https://huggingface.co/models?sort=downloads&search=eleutherai%2Fpythia+deduped)
* [OPT](https://huggingface.co/models?search=facebook/opt)
* [GALACTICA](https://huggingface.co/models?search=facebook/galactica)
* [GPT-J 6B](https://huggingface.co/EleutherAI/gpt-j-6B/tree/main)

You can automatically download a model from HF using the script `download-model.py`:

    python download-model.py organization/model

For example:

    python download-model.py facebook/opt-1.3b

To download a protected model, set env vars `HF_USER` and `HF_PASS` to your Hugging Face username and password (or [User Access Token](https://huggingface.co/settings/tokens)). The model's terms must first be accepted on the HF website.

#### GGML models

You can drop these directly into the `models/` folder, making sure that the file name contains `ggml` somewhere and ends in `.bin`.

#### GPT-4chan

<details>
<summary>
Instructions
</summary>

[GPT-4chan](https://huggingface.co/ykilcher/gpt-4chan) has been shut down from Hugging Face, so you need to download it elsewhere. You have two options:

* Torrent: [16-bit](https://archive.org/details/gpt4chan_model_float16) / [32-bit](https://archive.org/details/gpt4chan_model)
* Direct download: [16-bit](https://theswissbay.ch/pdf/_notpdf_/gpt4chan_model_float16/) / [32-bit](https://theswissbay.ch/pdf/_notpdf_/gpt4chan_model/)

The 32-bit version is only relevant if you intend to run the model in CPU mode. Otherwise, you should use the 16-bit version.

After downloading the model, follow these steps:

1. Place the files under `models/gpt4chan_model_float16` or `models/gpt4chan_model`.
2. Place GPT-J 6B's config.json file in that same folder: [config.json](https://huggingface.co/EleutherAI/gpt-j-6B/raw/main/config.json).
3. Download GPT-J 6B's tokenizer files (they will be automatically detected when you attempt to load GPT-4chan):

```
python download-model.py EleutherAI/gpt-j-6B --text-only
```

When you load this model in default or notebook modes, the "HTML" tab will show the generated text in 4chan format.
</details>

## Starting the web UI

    conda activate textgen
    cd text-generation-webui
    python server.py

Then browse to 

`http://localhost:7860/?__theme=dark`

Optionally, you can use the following command-line flags:

#### Basic settings

| Flag                                       | Description |
|--------------------------------------------|-------------|
| `-h`, `--help`                             | Show this help message and exit. |
| `--notebook`                               | Launch the web UI in notebook mode, where the output is written to the same text box as the input. |
| `--chat`                                   | Launch the web UI in chat mode. |
| `--multi-user`                             | Multi-user mode. Chat histories are not saved or automatically loaded. WARNING: this is highly experimental. |
| `--character CHARACTER`                    | The name of the character to load in chat mode by default. |
| `--model MODEL`                            | Name of the model to load by default. |
| `--lora LORA [LORA ...]`                   | The list of LoRAs to load. If you want to load more than one LoRA, write the names separated by spaces. |
| `--model-dir MODEL_DIR`                    | Path to directory with all the models. |
| `--lora-dir LORA_DIR`                      | Path to directory with all the loras. |
| `--model-menu`                             | Show a model menu in the terminal when the web UI is first launched. |
| `--no-stream`                              | Don't stream the text output in real time. |
| `--settings SETTINGS_FILE`                 | Load the default interface settings from this yaml file. See `settings-template.yaml` for an example. If you create a file called `settings.yaml`, this file will be loaded by default without the need to use the `--settings` flag. |
| `--extensions EXTENSIONS [EXTENSIONS ...]` | The list of extensions to load. If you want to load more than one extension, write the names separated by spaces. |
| `--verbose`                                | Print the prompts to the terminal. |

#### Model loader

| Flag                                       | Description |
|--------------------------------------------|-------------|
| `--loader LOADER`                          | Choose the model loader manually, otherwise, it will get autodetected. Valid options: transformers, autogptq, gptq-for-llama, exllama, exllama_hf, llamacpp, rwkv |

#### Accelerate/transformers

| Flag                                        | Description |
|---------------------------------------------|-------------|
| `--cpu`                                     | Use the CPU to generate text. Warning: Training on CPU is extremely slow.|
| `--auto-devices`                            | Automatically split the model across the available GPU(s) and CPU. |
|  `--gpu-memory GPU_MEMORY [GPU_MEMORY ...]` | Maximum GPU memory in GiB to be allocated per GPU. Example: `--gpu-memory 10` for a single GPU, `--gpu-memory 10 5` for two GPUs. You can also set values in MiB like `--gpu-memory 3500MiB`. |
| `--cpu-memory CPU_MEMORY`                   | Maximum CPU memory in GiB to allocate for offloaded weights. Same as above.|
| `--disk`                                    | If the model is too large for your GPU(s) and CPU combined, send the remaining layers to the disk. |
| `--disk-cache-dir DISK_CACHE_DIR`           | Directory to save the disk cache to. Defaults to `cache/`. |
| `--load-in-8bit`                            | Load the model with 8-bit precision (using bitsandbytes).|
| `--bf16`                                    | Load the model with bfloat16 precision. Requires NVIDIA Ampere GPU. |
| `--no-cache`                                | Set `use_cache` to False while generating text. This reduces the VRAM usage a bit with a performance cost. |
| `--xformers`                                | Use xformer's memory efficient attention. This should increase your tokens/s. |
| `--sdp-attention`                           | Use torch 2.0's sdp attention. |
| `--trust-remote-code`                       | Set trust_remote_code=True while loading a model. Necessary for ChatGLM and Falcon. |

#### Accelerate 4-bit

⚠️ Requires minimum compute of 7.0 on Windows at the moment.

| Flag                                        | Description |
|---------------------------------------------|-------------|
| `--load-in-4bit`                            | Load the model with 4-bit precision (using bitsandbytes). |
| `--compute_dtype COMPUTE_DTYPE`             | compute dtype for 4-bit. Valid options: bfloat16, float16, float32. |
| `--quant_type QUANT_TYPE`                   | quant_type for 4-bit. Valid options: nf4, fp4. |
| `--use_double_quant`                        | use_double_quant for 4-bit. |

#### llama.cpp

| Flag        | Description |
|-------------|-------------|
| `--threads` | Number of threads to use. |
| `--n_batch` | Maximum number of prompt tokens to batch together when calling llama_eval. |
| `--no-mmap` | Prevent mmap from being used. |
| `--mlock`   | Force the system to keep the model in RAM. |
| `--cache-capacity CACHE_CAPACITY`   | Maximum cache capacity. Examples: 2000MiB, 2GiB. When provided without units, bytes will be assumed. |
| `--n-gpu-layers N_GPU_LAYERS` | Number of layers to offload to the GPU. Only works if llama-cpp-python was compiled with BLAS. Set this to 1000000000 to offload all layers to the GPU. |
| `--n_ctx N_CTX` | Size of the prompt context. |
| `--llama_cpp_seed SEED` | Seed for llama-cpp models. Default 0 (random). |
| `--n_gqa N_GQA`         | grouped-query attention. Must be 8 for llama-2 70b. |
| `--rms_norm_eps RMS_NORM_EPS`  | 5e-6 is a good value for llama-2 models. |
| `--cpu`                        | Use the CPU version of llama-cpp-python instead of the GPU-accelerated version. |

#### AutoGPTQ

| Flag             | Description |
|------------------|-------------|
| `--triton`                     | Use triton. |
| `--no_inject_fused_attention`  | Disable the use of fused attention, which will use less VRAM at the cost of slower inference. |
| `--no_inject_fused_mlp`        | Triton mode only: disable the use of fused MLP, which will use less VRAM at the cost of slower inference. |
| `--no_use_cuda_fp16`           | This can make models faster on some systems. |
| `--desc_act`                   | For models that don't have a quantize_config.json, this parameter is used to define whether to set desc_act or not in BaseQuantizeConfig. |

#### ExLlama

| Flag             | Description |
|------------------|-------------|
|`--gpu-split`     | Comma-separated list of VRAM (in GB) to use per GPU device for model layers, e.g. `20,7,7` |
|`--max_seq_len MAX_SEQ_LEN`           | Maximum sequence length. |

#### GPTQ-for-LLaMa

| Flag                      | Description |
|---------------------------|-------------|
| `--wbits WBITS`           | Load a pre-quantized model with specified precision in bits. 2, 3, 4 and 8 are supported. |
| `--model_type MODEL_TYPE` | Model type of pre-quantized model. Currently LLaMA, OPT, and GPT-J are supported. |
| `--groupsize GROUPSIZE`   | Group size. |
| `--pre_layer PRE_LAYER [PRE_LAYER ...]`  | The number of layers to allocate to the GPU. Setting this parameter enables CPU offloading for 4-bit models. For multi-gpu, write the numbers separated by spaces, eg `--pre_layer 30 60`. |
| `--checkpoint CHECKPOINT` | The path to the quantized checkpoint file. If not specified, it will be automatically detected. |
| `--monkey-patch`          | Apply the monkey patch for using LoRAs with quantized models.
| `--quant_attn`         | (triton) Enable quant attention. |
| `--warmup_autotune`    | (triton) Enable warmup autotune. |
| `--fused_mlp`          | (triton) Enable fused mlp. |

#### DeepSpeed

| Flag                                  | Description |
|---------------------------------------|-------------|
| `--deepspeed`                         | Enable the use of DeepSpeed ZeRO-3 for inference via the Transformers integration. |
| `--nvme-offload-dir NVME_OFFLOAD_DIR` | DeepSpeed: Directory to use for ZeRO-3 NVME offloading. |
| `--local_rank LOCAL_RANK`             | DeepSpeed: Optional argument for distributed setups. |

#### RWKV

| Flag                            | Description |
|---------------------------------|-------------|
| `--rwkv-strategy RWKV_STRATEGY` | RWKV: The strategy to use while loading the model. Examples: "cpu fp32", "cuda fp16", "cuda fp16i8". |
| `--rwkv-cuda-on`                | RWKV: Compile the CUDA kernel for better performance. |

#### RoPE (for llama.cpp and ExLlama only)

| Flag             | Description |
|------------------|-------------|
|`--compress_pos_emb COMPRESS_POS_EMB` | Positional embeddings compression factor. Should typically be set to max_seq_len / 2048. |
|`--alpha_value ALPHA_VALUE`           | Positional embeddings alpha factor for NTK RoPE scaling. Scaling is not identical to embedding compression. Use either this or compress_pos_emb, not both. |

#### Gradio

| Flag                                  | Description |
|---------------------------------------|-------------|
| `--listen`                            | Make the web UI reachable from your local network. |
| `--listen-host LISTEN_HOST`           | The hostname that the server will use. |
| `--listen-port LISTEN_PORT`           | The listening port that the server will use. |
| `--share`                             | Create a public URL. This is useful for running the web UI on Google Colab or similar. |
| `--auto-launch`                       | Open the web UI in the default browser upon launch. |
| `--gradio-auth USER:PWD`              | set gradio authentication like "username:password"; or comma-delimit multiple like "u1:p1,u2:p2,u3:p3" |
| `--gradio-auth-path GRADIO_AUTH_PATH` | Set the gradio authentication file path. The file should contain one or more user:password pairs in this format: "u1:p1,u2:p2,u3:p3" |
| `--ssl-keyfile SSL_KEYFILE`           | The path to the SSL certificate key file. |
| `--ssl-certfile SSL_CERTFILE`         | The path to the SSL certificate cert file. |

#### API

| Flag                                  | Description |
|---------------------------------------|-------------|
| `--api`                               | Enable the API extension. |
| `--public-api`                        | Create a public URL for the API using Cloudfare. |
| `--api-blocking-port BLOCKING_PORT`   | The listening port for the blocking API. |
| `--api-streaming-port STREAMING_PORT` | The listening port for the streaming API. |

#### Multimodal

| Flag                                  | Description |
|---------------------------------------|-------------|
| `--multimodal-pipeline PIPELINE`      | The multimodal pipeline to use. Examples: `llava-7b`, `llava-13b`. |

## Presets

Inference settings presets can be created under `presets/` as yaml files. These files are detected automatically at startup.

The presets that are included by default are the result of a contest that received 7215 votes. More details can be found [here](https://github.com/oobabooga/oobabooga.github.io/blob/main/arena/results.md).

## Contributing

If you would like to contribute to the project, check out the [Contributing guidelines](https://github.com/oobabooga/text-generation-webui/wiki/Contributing-guidelines).

## Community

* Subreddit: https://www.reddit.com/r/oobaboogazz/
* Discord: https://discord.gg/jwZCF2dPQN
>>>>>>> Stashed changes
