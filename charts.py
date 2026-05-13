import io
import time
from datetime import datetime


def _dark_style(fig, ax):
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.tick_params(colors="#aaaaaa")
    for spine in ax.spines.values():
        spine.set_color("#333355")
    ax.yaxis.label.set_color("#aaaaaa")
    ax.xaxis.label.set_color("#aaaaaa")
    ax.title.set_color("white")


COLORS = ["#00d4ff", "#ff6b6b", "#ffd93d", "#6bcb77", "#c77dff", "#ff9f43"]


def latency_chart():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from prober import latency_history, probe_results

        if not latency_history or all(len(v) == 0 for v in latency_history.values()):
            return None, "⏳ No latency data yet — wait for probes to accumulate."

        fig, ax = plt.subplots(figsize=(11, 5))
        _dark_style(fig, ax)

        for i, (node_id, points) in enumerate(latency_history.items()):
            if len(points) < 2:
                continue
            name = probe_results.get(node_id, {}).get("name", node_id)
            times = [datetime.fromtimestamp(t) for t, _ in points]
            lats = [l for _, l in points]
            color = COLORS[i % len(COLORS)]
            ax.plot(times, lats, color=color, linewidth=2,
                    label=name, marker="o", markersize=3, alpha=0.9)
            ax.fill_between(times, lats, alpha=0.1, color=color)

        ax.set_title("📉 Node Latency Over Time (ms)", fontsize=13, pad=12)
        ax.set_ylabel("Latency (ms)")
        ax.set_xlabel("Time (UTC)")
        ax.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=9,
                  loc="upper right", framealpha=0.7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig.autofmt_xdate(rotation=30)
        ax.grid(color="#222244", linestyle="--", linewidth=0.5, alpha=0.7)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=110,
                    bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf, None

    except Exception as e:
        return None, f"❌ Chart error: {e}"


def traffic_chart(nodes_stats):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        names = [n["name"] for n in nodes_stats]
        tx = [round(n["traffic"]["tx"] / 1024 ** 3, 2) for n in nodes_stats]
        rx = [round(n["traffic"]["rx"] / 1024 ** 3, 2) for n in nodes_stats]

        x = np.arange(len(names))
        width = 0.38

        fig, ax = plt.subplots(figsize=(11, 5))
        _dark_style(fig, ax)

        bars_tx = ax.bar(x - width / 2, tx, width, label="↑ Upload (GB)",
                         color="#ff6b6b", alpha=0.85)
        bars_rx = ax.bar(x + width / 2, rx, width, label="↓ Download (GB)",
                         color="#00d4ff", alpha=0.85)

        for bar in list(bars_tx) + list(bars_rx):
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02,
                        f"{h}", ha="center", va="bottom",
                        color="white", fontsize=7)

        ax.set_title("📊 Node Traffic (GB)", fontsize=13, pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(names, color="white", fontsize=9)
        ax.set_ylabel("Gigabytes")
        ax.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=9, framealpha=0.7)
        ax.grid(axis="y", color="#222244", linestyle="--", linewidth=0.5, alpha=0.7)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=110,
                    bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf, None

    except Exception as e:
        return None, f"❌ Chart error: {e}"
