import os
import time
import json
from flask import Flask, jsonify
import psycopg2
import redis

import plotly.graph_objects as go
import plotly.io as pio

import networkx as nx
import math

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME")

# Redis
redis_client = redis.from_url(os.getenv("REDIS_URL"))

# Postgres
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="postgres"
    )

# init table
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS counter (id SERIAL PRIMARY KEY, value INT);")
    cur.execute("INSERT INTO counter (value) SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM counter);")
    conn.commit()
    cur.close()
    conn.close()

init_db()

# функции для постоения графа треугольника Паскаля
def build_pascal_graph(n_layers):
    G = nx.Graph()
    pos = {}

    for i in range(n_layers):
        for j in range(i + 1):
            val = math.comb(i, j)
            node = (i, j)

            G.add_node(node, value=val)
            pos[node] = (j - i / 2, -i)

            if i > 0:
                if j > 0:
                    G.add_edge((i - 1, j - 1), node)
                if j < i:
                    G.add_edge((i - 1, j), node)

    return G, pos


def make_traces(G, pos):

    edge_x, edge_y = [], []

    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]

        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="gray"),
        hoverinfo="none"
    )

    node_x, node_y, text = [], [], []

    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        text.append(str(G.nodes[n]["value"]))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=text,
        textposition="middle center",
        marker=dict(size=18, color="lightblue")
    )

    return edge_trace, node_trace

@app.route("/")
def home():

    max_layers = 8

    frames = []

    for n in range(1, max_layers + 1):

        G, pos = build_pascal_graph(n)
        edge_trace, node_trace = make_traces(G, pos)

        frames.append(go.Frame(
            data=[edge_trace, node_trace],
            name=str(n)
        ))

    fig = go.Figure(
        data=frames[0].data,
        frames=frames
    )

    fig.update_layout(
        title=APP_NAME + " — Pascal Triangle Graph",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        sliders=[{
            "steps": [
                {
                    "method": "animate",
                    "label": str(n),
                    "args": [
                        [str(n)],
                        {
                            "frame": {"duration": 600, "redraw": True},
                            "transition": {"duration": 300},
                            "mode": "immediate"
                        }
                    ]
                }
                for n in range(1, max_layers + 1)
            ]
        }]
    )

    graph_html = pio.to_html(fig, full_html=False)

    return f"""
    <html>
        <head>
            <title>{APP_NAME}</title>
        </head>
        <body>
            <h1>{APP_NAME}</h1>
            <p>Interactive Pascal Triangle Graph (NetworkX + Plotly)</p>
            {graph_html}
        </body>
    </html>
    """

@app.route("/visits")
def visits():
    cached = redis_client.get("visits")

    if cached:
        return jsonify({"total": int(cached), "cached": True})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("UPDATE counter SET value = value + 1 RETURNING value;")
    value = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    redis_client.setex("visits", 10, value)

    return jsonify({"total": value, "cached": False})

@app.route("/health")
def health():
    # DB check
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "connected"
    except:
        db_status = "error"

    # Redis check
    try:
        redis_client.ping()
        redis_status = "connected"
    except:
        redis_status = "error"

    return jsonify({
        "status": "ok",
        "db": db_status,
        "redis": redis_status
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
