# Chapter 11 Summary: Clusters and Job Queues
*High Performance Python, 3rd Edition*

---

## When to Cluster

Clustering makes sense when:
- A single machine (even with multiprocessing) cannot meet throughput or latency requirements
- You need **geographic redundancy**
- You need more RAM/CPU than a single machine can provide

But consider **vertical scaling first** — adding RAM or CPUs to one machine is simpler and cheaper than maintaining a cluster.

---

## Benefits of Clustering

- Scale beyond single-machine limits
- Geographic redundancy (survives regional outages)
- Heterogeneous software environments can improve robustness
- Unused idle time on existing machines can be utilized

---

## Drawbacks of Clustering

- Latency between machines
- Need to track which machines are up and running the right software version
- **System administration is the biggest cost** — machines fail (disk errors, network cards, power supplies, cosmic bit flips)
- Each additional machine adds management overhead
- Need a **documented restart plan** or a failure at the worst time will be very painful
- Queue backlog during downtime: do you have capacity to catch up?

### High-Profile Cluster Failures (Lessons)

**Knight Capital ($462M loss, 2012)**:
- Bug introduced during a software upgrade to 7 of 8 machines; the 8th ran old code
- Old flag was repurposed without removing the stale code path
- No second-reviewer process for upgrades
- **Lessons**: remove dead code, use checklists for upgrades, always have a second pair of eyes

**Skype 24-hour outage (2010)**:
- Overload caused Windows client crashes; ~40% of clients + 25% of supernodes went offline
- Restarting clients flooded the already-strained network → cascading failure
- **Lessons**: design for failure modes, test cascade scenarios, heterogeneous networks are more resilient

---

## Common Cluster Designs

- **Ad hoc local cluster**: cheap old machines — but old CPUs use more power and contribute less than one new fast machine
- **Cloud cluster** (AWS EC2, Azure): offloads hardware maintenance; supports spot pricing
- **Custom cluster**: InfiniBand networking, specialized RAID, GPU+CPU hybrid nodes
- **Decentralized** (BOINC-style): nodes join/leave dynamically; centralized coordination

### Software Architectures
| Pattern | Description |
|---|---|
| **Queue** | Workers pull tasks; results go to DB or next queue |
| **Pub/Sub** | Publishers push to topics; all subscribers get a copy |
| **Message passing (MPI)** | Processes communicate directly; expert-level |

---

## IPython Parallel

Easy clustering for research and Jupyter-based workflows:

```python
import ipyparallel as ipp
c = ipp.Client()
dview = c[:]   # direct view of all engines

with dview.sync_imports():
    import os

results = dview.apply_sync(estimate_pi, nbr_samples_per_worker)
```

- Start engines: `ipcluster start -n 4`
- Push/pull data to all engines: `dview.push({'data': ...})` / `dview.pull('data')`
- Supports MPI, async jobs, remote debugging
- Works on local machines, AWS EC2, Azure, supercomputers (via ElastiCluster)

---

## Message Brokering

For production systems, use a message broker — handles node failures, backlogs, and variable producer/consumer rates.

### Queue Topology
- Producer puts jobs on a queue
- Workers pull and process when ready
- Handles imbalance between production and consumption rates
- Messages survive consumer crashes (delivery guarantees)

Key questions when choosing a queue:
- What happens when the queue fills up (memory exhaustion)?
- What if the queue server goes offline?
- Can messages be distributed across nodes with redundancy?
- Do consumers need to acknowledge processing?

### Pub/Sub Topology
- Publishers push to **topics**; all subscriber groups receive a copy
- Within each subscriber group, **only one consumer** processes each message (load balancing)
- Consumers can be added/removed dynamically
- Enables **pipeline chaining**: consume from topic A → transform → publish to topic B

Key questions:
- At-least-once vs. at-most-once delivery guarantees?
- Single points of failure?
- Message archiving and replay support?

### Popular Tools
| Tool | Notes |
|---|---|
| **RabbitMQ** | Reliable, widely used; AMQP protocol |
| **Kafka** | High-throughput, log-based; great for replay |
| **ZeroMQ** | Low-level, fast; used in Jupyter, Spotify |
| **Celery** | Python-native async task queue; uses RabbitMQ/Redis |
| **Airflow / Luigi** | DAG-based job orchestration; widely used in data science |
| **AWS SQS** | Managed, cloud-native; easy to start with |

---

## Docker

Docker solves the **reproducible environment** problem, which is especially painful in clusters.

### Performance
- **No CPU/memory overhead** on Linux — Docker uses OS-level virtualization (cgroups), not hardware virtualization
- On macOS/Windows: Docker runs Linux in a hardware VM (VirtualBox) → some overhead
- NumPy diffusion benchmark: **host = 0.859 s vs. Docker = 0.842 s** (no meaningful difference)

### Performance Gotchas
- Large build context → slow builds (use `.dockerignore`)
- Layered filesystem slower than host filesystem for heavy I/O (use host mounts)
- Virtual network adds slight overhead (change network driver to mitigate)
- GPUs: use `nvidia-docker` and `--device` flags

### Docker Best Practices for Performance Code
```dockerfile
FROM python:3.12-slim
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  # cache layer separately
COPY . .
CMD ["python", "./script.py"]
```

- Copy `requirements.txt` before source code to maximize build cache reuse
- Tag images with both `latest` and descriptive version tags
- Use a **container registry** (Docker Hub, ECR) to share images across team

### Advantages
- Reproducible environments eliminate "works on my machine" bugs
- Easy to re-run old versions for performance regression testing
- `docker pull` replaces complex setup instructions
- Kubernetes + Docker enables auto-scaling and resource-aware scheduling

---

## Key Takeaways

1. Prefer vertical scaling (more RAM/CPU on one machine) before clustering
2. Always document restart procedures — you'll need them at the worst moment
3. Clustering adds system administration overhead; budget for it
4. Knight Capital and Skype failures highlight the importance of upgrade checklists and failure testing
5. Use established message brokers (RabbitMQ, Kafka, Celery) rather than rolling your own
6. Docker has negligible performance overhead on Linux and massively improves reproducibility
7. IPython Parallel is a quick entry point for research-oriented cluster work
