import textwrap
from pathlib import Path
from typing import List, Dict, Tuple

from pydot import Dot, Node, Edge


class DeclareModelBuilder:

    def __init__(self, constraints: List[Tuple[str, str, str, str]], wrap_width: int = 20):
        self.constraints: List[Tuple[str, str, str, str]] = constraints
        self.wrap_width: int = wrap_width

    def generate_model(self) -> None:
        DECLARE_MODEL_PATH: Path = Path(__file__).parents[3] / 'frontend' / 'src' / 'declare_model.png'
        graph: Dot = Dot(graph_type='digraph', rankdir='LR', dpi="200")
        graph.set('overlap', 'false')

        activities: set[str] = set()
        parsed: List[Tuple[str, str, str, str]] = []
        for constraint in self.constraints:
            parsed.append((constraint[0], constraint[1], constraint[2], constraint[3]))
            activities.update({constraint[1], constraint[2]})

        for activity in activities:
            node_label: str = self.wrap_label(label=activity, width=self.wrap_width)
            graph.add_node(Node(
                name=activity,
                label=node_label,
                fillcolor="#f0f0f0",
                style='rounded,filled',
                shape="box",
                fontsize="14",
                width="1.5",
                height="0.7"
            ))

        for idx, (template, source_activity, target_activity, data_condition) in enumerate(parsed):
            template_node_id: str = f"icon_{idx}"
            icon_path: Path = self.get_img_file_mapping(template)

            graph.add_node(Node(
                name=template_node_id,
                label='',
                shape='none',
                image=str(icon_path),
                imagescale='true',
                fixedsize='true',
                width='0.2',
                height='0.2'
            ))

            edge_props = dict(arrowhead='none', tailport='e', headport='w')
            edge_left = Edge(source_activity, template_node_id, **edge_props)
            edge_right = Edge(template_node_id, target_activity, **edge_props)

            target_edge = edge_left if 'Precedence' in template else edge_right
            target_edge.set('label', data_condition)
            target_edge.set('fontsize', '12')
            target_edge.set('labelfontcolor', '#000000')
            target_edge.set('labeldistance', '2')
            target_edge.set('labelangle', '0')

            graph.add_edge(edge_left)
            graph.add_edge(edge_right)

        try:
            graph.write_png(DECLARE_MODEL_PATH)
            print(f"Model PNG successfully saved to {DECLARE_MODEL_PATH}")
        except Exception as e:
            print(f"Failed to write model PNG file to {DECLARE_MODEL_PATH}: {e}")

    @staticmethod
    def wrap_label(label: str, width: int) -> str:
        lines: List[str] = textwrap.wrap(text=label, width=width, break_long_words=True)
        for i in range(len(lines) - 1):
            lines[i] = lines[i] + "-"
        return "\n".join(lines)

    @staticmethod
    def get_img_file_mapping(template: str) -> Path:
        BASE_PATH: Path = Path(__file__).parents[3] / 'assets/easydeclare'
        mapping: Dict[str, Path] = {
            "Precedence": BASE_PATH / 'precedence.png',
            "Alternate Precedence": BASE_PATH / 'alternate_precedence.png',
            "Chain Precedence": BASE_PATH / 'chain_precedence.png',
            "Response": BASE_PATH / 'response.png',
            "Alternate Response": BASE_PATH / 'alternate_response.png',
            "Chain Response": BASE_PATH / 'chain_response.png',
            "Responded Existence": BASE_PATH / 'responded_existence.png',
            "Not Precedence": BASE_PATH / 'not_precedence.png',
            "Not Alternate Precedence": BASE_PATH / 'not_alternate_precedence.png',
            "Not Chain Precedence": BASE_PATH / 'not_chain_precedence.png',
            "Not Response": BASE_PATH / 'not_response.png',
            "Not Alternate Response": BASE_PATH / 'not_alternate_response.png',
            "Not Chain Response": BASE_PATH / 'not_chain_response.png',
            "Not Responded Existence": BASE_PATH / 'not_responded_existence.png',
        }

        return BASE_PATH / mapping.get(template)
