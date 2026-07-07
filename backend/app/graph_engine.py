"""
MSME FinGenome — Graph / Network Analysis Engine
==================================================
Constructs and analyzes the economic network graph from UPI transaction data.
Each MSME is a node. Edges represent financial relationships (supplier/customer).

This is the "secret weapon" — the dimension no other hackathon team will have.
It reveals:
  - Supply chain position and dependencies
  - Concentration risk (single customer/supplier exposure)
  - Cascade risk (if a key counterparty defaults, who's affected?)
  - Community detection (industry clusters)
  - Economic ecosystem health
"""

import networkx as nx
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict

from app.models import (
    MSMEDataPackage, NetworkNode, NetworkEdge, MSMENetwork
)


class EconomicGraphEngine:
    """Builds and analyzes the MSME economic network."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._node_data: Dict[str, dict] = {}
        self._edge_data: Dict[Tuple[str, str], dict] = {}

    def build_graph(self, packages: List[MSMEDataPackage],
                     genomes: Dict[str, dict] = None):
        """
        Build the economic network from all MSME data packages.

        Args:
            packages: List of all MSME data packages
            genomes: Optional dict of business_id -> genome data for node enrichment
        """
        self.graph.clear()
        self._node_data.clear()
        self._edge_data.clear()

        # Add all MSMEs as nodes
        for pkg in packages:
            eid = pkg.entity.business_id
            health_score = 50.0
            risk_grade = "B"
            if genomes and eid in genomes:
                health_score = genomes[eid].get("overall_score", 50.0)
                risk_grade = genomes[eid].get("risk_grade", "B")

            self.graph.add_node(eid)
            self._node_data[eid] = {
                "name": pkg.entity.name,
                "industry": pkg.entity.industry.value,
                "health_score": health_score,
                "risk_grade": risk_grade if isinstance(risk_grade, str) else risk_grade.value,
                "category": pkg.entity.category.value,
            }

        # Build edges from UPI transactions
        edge_volumes: Dict[Tuple[str, str], float] = defaultdict(float)
        edge_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        for pkg in packages:
            eid = pkg.entity.business_id
            for txn in pkg.upi_transactions:
                cid = txn.counterparty_id

                # Only create edges between known MSMEs in our network
                if cid in self._node_data:
                    if txn.direction == "inflow":
                        edge_key = (cid, eid)  # Money flows from counterparty to this MSME
                    else:
                        edge_key = (eid, cid)  # Money flows from this MSME to counterparty

                    edge_volumes[edge_key] += txn.amount
                    edge_counts[edge_key] += 1
                else:
                    # External counterparty — add as external node
                    if cid not in self._node_data:
                        self.graph.add_node(cid)
                        self._node_data[cid] = {
                            "name": txn.counterparty_name,
                            "industry": "External",
                            "health_score": 50.0,
                            "risk_grade": "N/A",
                            "category": "external",
                        }

                    if txn.direction == "inflow":
                        edge_key = (cid, eid)
                    else:
                        edge_key = (eid, cid)

                    edge_volumes[edge_key] += txn.amount
                    edge_counts[edge_key] += 1

        # Normalize edge strengths
        max_volume = max(edge_volumes.values()) if edge_volumes else 1
        for (src, tgt), volume in edge_volumes.items():
            strength = min(1.0, volume / max_volume)
            self.graph.add_edge(src, tgt, weight=strength, volume=volume,
                                count=edge_counts[(src, tgt)])
            self._edge_data[(src, tgt)] = {
                "volume": volume,
                "count": edge_counts[(src, tgt)],
                "strength": strength,
            }

    def add_node(self, node: NetworkNode):
        """Add a node dynamically without rebuilding the entire graph."""
        self.graph.add_node(node.id)
        self._node_data[node.id] = {
            "name": node.name,
            "industry": node.industry,
            "health_score": node.health_score,
            "risk_grade": node.risk_grade,
            "category": node.category,
        }

    def get_msme_network(self, business_id: str, depth: int = 1) -> MSMENetwork:
        """
        Extract the local network around a specific MSME.

        Args:
            business_id: The MSME to center the network on
            depth: How many hops to include (1 = direct connections only)

        Returns:
            MSMENetwork with nodes, edges, metrics, and risk narrative
        """
        if business_id not in self.graph:
            return MSMENetwork(
                primary_msme_id=business_id,
                nodes=[], edges=[], metrics={},
                risk_narrative="No network data available for this MSME."
            )

        # Get ego network (local neighborhood)
        ego_nodes = {business_id}
        current_frontier = {business_id}
        for _ in range(depth):
            next_frontier = set()
            for node in current_frontier:
                next_frontier.update(self.graph.predecessors(node))
                next_frontier.update(self.graph.successors(node))
            ego_nodes.update(next_frontier)
            current_frontier = next_frontier

        # Limit to manageable size for visualization
        if len(ego_nodes) > 30:
            # Keep the most important connections
            edges_with_primary = []
            for node in ego_nodes:
                if node == business_id:
                    continue
                vol = 0
                if (business_id, node) in self._edge_data:
                    vol += self._edge_data[(business_id, node)]["volume"]
                if (node, business_id) in self._edge_data:
                    vol += self._edge_data[(node, business_id)]["volume"]
                edges_with_primary.append((node, vol))
            edges_with_primary.sort(key=lambda x: x[1], reverse=True)
            ego_nodes = {business_id} | {n for n, _ in edges_with_primary[:25]}

        # Build node list
        nodes = []
        for nid in ego_nodes:
            nd = self._node_data.get(nid, {})
            nodes.append(NetworkNode(
                id=nid,
                name=nd.get("name", nid),
                industry=nd.get("industry", "Unknown"),
                health_score=nd.get("health_score", 50.0),
                risk_grade=nd.get("risk_grade", "N/A"),
                is_primary=(nid == business_id),
                category=nd.get("category", "external"),
                size=2.0 if nid == business_id else 1.0,
            ))

        # Build edge list
        edges = []
        for (src, tgt), edata in self._edge_data.items():
            if src in ego_nodes and tgt in ego_nodes:
                # Determine direction relative to primary
                is_critical = False
                direction = "outflow"
                if tgt == business_id:
                    direction = "inflow"
                elif src == business_id:
                    direction = "outflow"
                else:
                    direction = "bidirectional"

                # Check if critical (>30% of total volume)
                total_inflow = sum(
                    ed["volume"] for (s, t), ed in self._edge_data.items()
                    if t == business_id
                )
                total_outflow = sum(
                    ed["volume"] for (s, t), ed in self._edge_data.items()
                    if s == business_id
                )
                if direction == "inflow" and total_inflow > 0:
                    is_critical = (edata["volume"] / total_inflow) > 0.30
                elif direction == "outflow" and total_outflow > 0:
                    is_critical = (edata["volume"] / total_outflow) > 0.30

                edges.append(NetworkEdge(
                    source=src,
                    target=tgt,
                    transaction_volume=round(edata["volume"], 2),
                    transaction_count=edata["count"],
                    direction=direction,
                    strength=round(edata["strength"], 3),
                    is_critical=is_critical,
                ))

        # Compute network metrics
        metrics = self._compute_network_metrics(business_id, ego_nodes)

        # Generate risk narrative
        narrative = self._generate_risk_narrative(business_id, nodes, edges, metrics)

        return MSMENetwork(
            primary_msme_id=business_id,
            nodes=nodes,
            edges=edges,
            metrics=metrics,
            risk_narrative=narrative,
        )

    def _compute_network_metrics(self, business_id: str,
                                   ego_nodes: set) -> Dict[str, float]:
        """Compute graph-theoretic metrics for the MSME."""
        metrics = {}

        # Degree centrality (in the full graph)
        if len(self.graph) > 1:
            dc = nx.degree_centrality(self.graph)
            metrics["degree_centrality"] = round(dc.get(business_id, 0), 4)
        else:
            metrics["degree_centrality"] = 0.0

        # In/Out degree
        metrics["in_degree"] = self.graph.in_degree(business_id)
        metrics["out_degree"] = self.graph.out_degree(business_id)
        metrics["total_connections"] = metrics["in_degree"] + metrics["out_degree"]

        # Concentration risk (HHI on inflows)
        inflow_volumes = {}
        for (src, tgt), edata in self._edge_data.items():
            if tgt == business_id:
                inflow_volumes[src] = edata["volume"]

        total_inflow = sum(inflow_volumes.values())
        if total_inflow > 0 and inflow_volumes:
            hhi = sum((v / total_inflow) ** 2 for v in inflow_volumes.values())
            metrics["inflow_hhi"] = round(hhi, 4)
            metrics["concentration_risk"] = round(hhi * 100, 1)
            top_customer_id = max(inflow_volumes, key=inflow_volumes.get)
            metrics["top_customer_share"] = round(
                inflow_volumes[top_customer_id] / total_inflow * 100, 1
            )
        else:
            metrics["inflow_hhi"] = 0.0
            metrics["concentration_risk"] = 0.0
            metrics["top_customer_share"] = 0.0

        # Outflow concentration
        outflow_volumes = {}
        for (src, tgt), edata in self._edge_data.items():
            if src == business_id:
                outflow_volumes[tgt] = edata["volume"]

        total_outflow = sum(outflow_volumes.values())
        if total_outflow > 0 and outflow_volumes:
            out_hhi = sum((v / total_outflow) ** 2 for v in outflow_volumes.values())
            metrics["outflow_hhi"] = round(out_hhi, 4)
            metrics["supplier_concentration"] = round(out_hhi * 100, 1)
        else:
            metrics["outflow_hhi"] = 0.0
            metrics["supplier_concentration"] = 0.0

        # Network health score (average health of connected nodes)
        connected_scores = []
        for nid in ego_nodes:
            if nid != business_id and nid in self._node_data:
                connected_scores.append(self._node_data[nid]["health_score"])
        metrics["avg_network_health"] = round(
            np.mean(connected_scores) if connected_scores else 50.0, 1
        )

        # Cascade risk (what % of revenue comes from unhealthy counterparties?)
        at_risk_volume = 0
        for src, vol in inflow_volumes.items():
            if src in self._node_data and self._node_data[src]["health_score"] < 40:
                at_risk_volume += vol
        metrics["cascade_risk_pct"] = round(
            at_risk_volume / total_inflow * 100 if total_inflow > 0 else 0, 1
        )

        # Total transaction volume
        metrics["total_inflow_volume"] = round(total_inflow, 2)
        metrics["total_outflow_volume"] = round(total_outflow, 2)

        return metrics

    def _generate_risk_narrative(self, business_id: str,
                                   nodes: List[NetworkNode],
                                   edges: List[NetworkEdge],
                                   metrics: Dict[str, float]) -> str:
        """Generate natural language narrative about network risks."""
        name = self._node_data.get(business_id, {}).get("name", business_id)
        parts = []

        # Connection summary
        total = metrics.get("total_connections", 0)
        parts.append(f"{name} operates within a network of {total} direct trading relationships")

        # Concentration risk
        conc = metrics.get("concentration_risk", 0)
        top_share = metrics.get("top_customer_share", 0)
        if conc > 50:
            parts.append(f"⚠️ HIGH concentration risk detected — top customer represents {top_share:.0f}% of inflows")
        elif conc > 25:
            parts.append(f"Moderate concentration — top customer at {top_share:.0f}% of inflows")
        else:
            parts.append(f"Well-diversified inflow base across multiple counterparties")

        # Cascade risk
        cascade = metrics.get("cascade_risk_pct", 0)
        if cascade > 20:
            parts.append(f"🔴 Cascade risk: {cascade:.0f}% of revenue comes from financially stressed counterparties")
        elif cascade > 10:
            parts.append(f"⚠️ {cascade:.0f}% of revenue linked to at-risk counterparties — monitor closely")

        # Network health
        net_health = metrics.get("avg_network_health", 50)
        if net_health > 65:
            parts.append(f"The surrounding network is healthy (avg score: {net_health:.0f}/100)")
        elif net_health < 40:
            parts.append(f"Concerning: surrounding network shows stress (avg score: {net_health:.0f}/100)")

        # Critical edges
        critical = [e for e in edges if e.is_critical]
        if critical:
            parts.append(f"{len(critical)} critical dependencies identified (>30% of flow)")

        return ". ".join(parts) + "."

    def get_full_graph_data(self) -> dict:
        """Return the complete graph data for full network visualization."""
        nodes = []
        for nid, nd in self._node_data.items():
            nodes.append({
                "id": nid,
                "name": nd.get("name", nid),
                "industry": nd.get("industry", "Unknown"),
                "health_score": nd.get("health_score", 50.0),
                "risk_grade": nd.get("risk_grade", "N/A"),
                "category": nd.get("category", "external"),
            })

        edges = []
        for (src, tgt), ed in self._edge_data.items():
            edges.append({
                "source": src,
                "target": tgt,
                "volume": round(ed["volume"], 2),
                "count": ed["count"],
                "strength": round(ed["strength"], 3),
            })

        return {"nodes": nodes, "edges": edges}
