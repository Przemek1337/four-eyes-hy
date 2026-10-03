from foureyes.core.control import Control, register


@register
class SourceStage(Control):
    """Baseline: where data came from decides labels and the sticky data class."""
    id = "source.stage"
    phases = ("pre", "post")
    hidden = True

    def evaluate(self, ctx, phase):
        req = ctx.request
        if phase == "pre" and req.kind == "model":
            identity = f"channel:{req.channel}"
        elif phase == "post" and req.kind == "tool":
            identity = f"mcp:{req.tool}"
        else:
            return None
        entry = ctx.policy.source_for(identity)
        ctx.source = identity
        ctx.source_labels = entry["labels"]
        for label in entry["labels"]:
            ctx.session.add_label(label, f"source {identity}")
        ctx.session.raise_class(entry["class"], ctx.policy.class_order, f"source {identity}", identity)
        return None
