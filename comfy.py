#!/usr/bin/env python3
"""Minimal ComfyUI txt2img client for cover insets.

Square 512x512 on purpose: the banner's artwork slot is a 300px square, and
512 is SD1.5's native training size — asking a 1.5 checkpoint for a wide
banner-shaped latent is what produces duplicated subjects and mush.
"""
import json, sys, time, urllib.parse, urllib.request, uuid

HOST = "http://127.0.0.1:8188"
CKPT = "v1-5-pruned-emaonly.safetensors"


def _post(path, payload):
    r = urllib.request.urlopen(urllib.request.Request(
        HOST + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}), timeout=60)
    return json.loads(r.read())


def generate(prompt, negative, seed, out_path, steps=30, cfg=7.5):
    cid = str(uuid.uuid4())
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": steps, "cfg": cfg,
                         "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "denoise": 1.0, "model": ["1", 0],
                         "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode",
              "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "cover", "images": ["6", 0]}},
    }
    # ⚠️ /history is keyed on the SERVER's prompt_id, not the client_id you
    # send. Polling for your own client_id matches nothing and spins forever
    # while the job has already finished.
    pid = _post("/prompt", {"prompt": wf, "client_id": cid})["prompt_id"]
    for _ in range(180):
        time.sleep(2)
        h = json.loads(urllib.request.urlopen(
            f"{HOST}/history/{pid}", timeout=30).read())
        run = h.get(pid)
        if not run:
            continue
        outs = run.get("outputs", {}).get("7", {}).get("images", [])
        if outs:
            im = outs[0]
            q = urllib.parse.urlencode({"filename": im["filename"],
                                        "subfolder": im.get("subfolder", ""),
                                        "type": im.get("type", "output")})
            open(out_path, "wb").write(
                urllib.request.urlopen(HOST + "/view?" + q, timeout=60).read())
            return out_path
    raise SystemExit("timed out waiting for ComfyUI")


if __name__ == "__main__":
    import urllib.parse
    generate(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
    print("wrote", sys.argv[4])
