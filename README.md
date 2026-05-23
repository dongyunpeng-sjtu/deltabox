# DeltaBox

**Scaling Stateful AI Agents with Millisecond-Level Sandbox Checkpoint/Rollback**

[**📄 Paper (PDF)**](assets/deltabox-paper.pdf) &nbsp;|&nbsp;
[**📡 arXiv:2605.22781**](https://arxiv.org/abs/2605.22781) &nbsp;|&nbsp;
[**🌐 Project page**](https://dongyunpeng-sjtu.github.io/deltabox/)

---

LLM-powered AI agents require high-frequency state exploration
(test-time tree search, reinforcement learning training fan-out), but
today's sandbox mechanisms duplicate the entire filesystem and process
state on every checkpoint, paying hundreds of milliseconds to seconds
per operation. DeltaBox eliminates this duplication by only capturing
the *changes* between consecutive checkpoints, delivering
**millisecond-level checkpoint and rollback** through co-designed
OS-level mechanisms.

## Key Results

| Metric | DeltaBox | Best baseline | Speed-up |
|---|---:|---:|---:|
| Checkpoint latency (mean) | **14 ms** | 49 ms (Docker commit) | 3.5× |
| Rollback latency (mean)   | **5 ms**  | 152 ms (copytree+replay) | 30× |
| End-to-end MCTS overhead  | **3–6 %** | 47–77 % (FC-Diff / CubeSandbox) | 12–25× |

(See [the project page](https://dongyunpeng-sjtu.github.io/deltabox/)
for full results across SWE-bench MCTS and RL training fan-out.)

## Authors

Yunpeng Dong<sup>1</sup>, Jingkai He<sup>1,2</sup>,
Yuze Hou<sup>1</sup>, **Dong Du<sup>1,2</sup>** (📧),
Zhonghu Xu<sup>3</sup>, Si Yu<sup>3</sup>,
Yubin Xia<sup>1,2</sup>, Haibo Chen<sup>1,2</sup>

<sup>1</sup> Institute of Parallel and Distributed Systems, Shanghai Jiao Tong University<br>
<sup>2</sup> Engineering Research Center for Domain-specific Operating Systems, Ministry of Education, China<br>
<sup>3</sup> Huawei Technologies Co., Ltd.

Contact: [Dong.Du@sjtu.edu.cn](mailto:Dong.Du@sjtu.edu.cn)

## Code Release

The artifacts (kernel patch, userspace controller, benchmark scripts)
are not currently public. We plan to release the code after
publication. If you are interested in early access for academic
collaboration, please reach out to the corresponding author.

## Citation

```bibtex
@article{dong2026deltabox,
  title         = {DeltaBox: Scaling Stateful AI Agents with Millisecond-Level Sandbox Checkpoint/Rollback},
  author        = {Dong, Yunpeng and He, Jingkai and Hou, Yuze and Du, Dong and Xu, Zhonghu and Yu, Si and Xia, Yubin and Chen, Haibo},
  year          = {2026},
  eprint        = {2605.22781},
  archivePrefix = {arXiv},
  primaryClass  = {cs.OS},
  url           = {https://arxiv.org/abs/2605.22781}
}
```

---

⭐ **If this work is helpful, please consider starring the repo to support us.**

*This repository hosts the [project landing page](https://dongyunpeng-sjtu.github.io/deltabox/).
For site deployment / maintenance, see [`DEPLOY.md`](DEPLOY.md).*
