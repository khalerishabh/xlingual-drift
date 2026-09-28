import json

import pytest

from eval.run_grid import ServingMismatch, check_cells_match_server, check_log_matches_server

A100_FP8 = {"model": "Qwen/Qwen3.6-27B-FP8", "revision": "abc123", "vllm_version": "0.19.1",
            "gpu_name": "NVIDIA A100-SXM4-40GB"}
CFG = {"serving": {"model": "Qwen/Qwen3.6-27B-FP8"},
       "cells": [{"name": "c", "policy": "openai_compat", "model": "Qwen/Qwen3.6-27B-FP8"}]}


def write_log(tmp_path, *servings):
    path = tmp_path / "log.jsonl"
    path.write_text("".join(json.dumps({"episode_key": f"k{i}", "policy": "openai_compat", "serving": s}) + "\n"
                            for i, s in enumerate(servings)), encoding="utf-8")
    return path


def test_same_backbone_on_another_gpu_is_allowed(tmp_path, capsys):
    log = write_log(tmp_path, A100_FP8)
    check_log_matches_server(log, {**A100_FP8, "gpu_name": "NVIDIA A100-SXM4-80GB"})
    assert "note:" in capsys.readouterr().out


@pytest.mark.parametrize("key,value", [("model", "Qwen/Qwen3.6-27B"), ("revision", "def456"), ("vllm_version", "0.20.0")])
def test_any_backbone_change_is_refused(tmp_path, key, value):
    log = write_log(tmp_path, A100_FP8)
    with pytest.raises(ServingMismatch):
        check_log_matches_server(log, {**A100_FP8, key: value})


def test_mismatch_deep_in_log_is_still_caught(tmp_path):
    log = write_log(tmp_path, {**A100_FP8, "gpu_name": "other"}, {**A100_FP8, "revision": "old"})
    with pytest.raises(ServingMismatch):
        check_log_matches_server(log, A100_FP8)


def test_config_must_match_what_the_server_runs():
    check_cells_match_server(A100_FP8, CFG)
    with pytest.raises(ServingMismatch):
        check_cells_match_server({**A100_FP8, "model": "Qwen/Qwen3.6-27B"}, CFG)
