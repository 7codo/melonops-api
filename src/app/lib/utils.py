from langfuse.api.resources.trace.client import Traces


def extract_usage_from_traces(traces: Traces):
    model_totals = {}

    for trace in traces.data:
        if not trace.output or "response" not in trace.output:
            continue
        responses = trace.output["response"]

        trace_cost = trace.total_cost

        for response in responses:
            model_name = response.get("response_metadata", {}).get("model_name")
            if model_name is None:
                continue

            if model_name not in model_totals:
                model_totals[model_name] = {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                }

            model_totals[model_name]["total_cost"] += trace_cost

            token_usage = None
            response_metadata = response.get("response_metadata", {})
            usage_metadata = response.get("usage_metadata", {})

            if "token_usage" in response_metadata:
                token_usage = response_metadata["token_usage"]
            elif usage_metadata:
                token_usage = {
                    "prompt_tokens": usage_metadata.get("input_tokens", 0),
                    "completion_tokens": usage_metadata.get("output_tokens", 0),
                    "total_tokens": usage_metadata.get("total_tokens", 0),
                }

            if token_usage:
                model_totals[model_name]["total_input_tokens"] += token_usage.get(
                    "prompt_tokens", 0
                )
                model_totals[model_name]["total_output_tokens"] += token_usage.get(
                    "completion_tokens", 0
                )
                model_totals[model_name]["total_tokens"] += token_usage.get(
                    "total_tokens", 0
                )

    return model_totals
