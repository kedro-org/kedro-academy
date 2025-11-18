import base64
from io import BytesIO
from typing import Literal, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from PIL import Image

from .data_models import DamageAssessment


# Agent state representation
class AgentState(TypedDict):
    image_dataset: dict[str, any]  # all candidate images (ordered)
    image_paths: list[str]
    idx: int  # current index into image_dataset
    count: int  # how many images processed so far (must not exceed 5)
    current_image: Optional[
        str
    ]  # path of the image currently being processed (or None)
    results: list[DamageAssessment]
    max_images: int  # maximum number of images to process
    confidence_threshold: float  # confidence threshold for stopping criteria


# Helper functions
def image_file_to_data_url(image: Image) -> str:
    """
    Reads pillow image and returns a data URL (base64) for safe model ingestion.
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def pick_next_image(state: AgentState) -> AgentState:
    """
    Picks the next image path if:
      - we have not exceeded 5 processed images, and
      - there are still images left in image_paths
    Otherwise, leaves current_image as None so the graph can END.
    """
    next_state = dict(state)
    if next_state["count"] >= next_state["max_images"]:
        next_state["current_image"] = None
        return next_state

    if next_state["idx"] < len(next_state["image_dataset"]):
        next_state["current_image"] = list(next_state["image_dataset"].keys())[
            next_state["idx"]
        ]
    else:
        next_state["current_image"] = None
    return next_state


def analyze_image(state: AgentState, model, prompt) -> AgentState:
    """
    Sends the current image to a vision-capable chat model and appends the analysis.
    """
    next_state = dict(state)
    img_path = next_state.get("current_image")

    if not img_path:
        # Nothing to do
        return next_state
    data_url = image_file_to_data_url(next_state["image_dataset"][img_path]())

    msg = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "source_type": "base64",
                "data": data_url,
                "mime_type": "image/jpeg",
            },
        ]
    )
    resp = model.with_structured_output(DamageAssessment).invoke([msg])

    next_state["results"].append(
        {
            "image": img_path,
            "analysis": resp,
        }
    )
    # Advance the pointer and count
    next_state["idx"] += 1
    next_state["count"] += 1
    # Clear current
    next_state["current_image"] = None
    return next_state


def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """
    If we've processed 5 images OR no more images are left, END.
    Otherwise, CONTINUE.
    """
    if state["count"] >= state["max_images"]:
        return "end"
    if state["results"][-1]["analysis"].confidence > state["confidence_threshold"]:
        return "end"
    if state["idx"] >= len(state["image_dataset"]):
        return "end"
    return "continue"


# Node functions
def build_graph(model: ChatOpenAI, prompt):
    """Build the state graph for image analysis."""
    g = StateGraph(AgentState)

    # Bind model to the analyze node with a closure
    def analyze_node(state: AgentState) -> AgentState:
        return analyze_image(state, model, prompt)

    g.add_node("pick_next_image", pick_next_image)
    g.add_node("analyze_image", analyze_node)

    g.set_entry_point("pick_next_image")

    # pick_next_image -> if there is an image -> analyze; else end
    def has_image(state: AgentState) -> Literal["analyze", "end"]:
        return "analyze" if state.get("current_image") else "end"

    g.add_conditional_edges(
        "pick_next_image",
        has_image,
        {
            "analyze": "analyze_image",
            "end": END,
        },
    )

    # analyze_image -> continue cycling until 5 are processed or the list ends
    g.add_conditional_edges(
        "analyze_image",
        should_continue,
        {
            "continue": "pick_next_image",
            "end": END,
        },
    )

    return g.compile()


def init_state(claims_pics, max_images, confidence_threshold):
    """
    Initialize the agent state for image analysis.
    """
    state = {
        "max_images": max_images,
        "confidence_threshold": confidence_threshold,
        "image_paths": list(claims_pics.keys()),
        "image_dataset": claims_pics,
        "current_image": None,
        "idx": 0,
        "count": 0,
        "results": [],
    }
    return state


def invoke_graph(graph, init_state):
    """
    Invoke the state graph with the initial state.
    """
    final_state = graph.invoke(init_state)
    res = {
        final_state["results"][i]["image"]: final_state["results"][i][
            "analysis"
        ].model_dump()
        for i in range(len(final_state["results"]))
    }
    return res
