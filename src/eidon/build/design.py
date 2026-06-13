import warnings

DESIGNS = {}


def _register(func):
    DESIGNS[func.__name__] = func
    return func


def build_design(
    name: str, participant_ids: list[str], item_ids: list[str], conditions: list[str]
) -> dict[str, list[tuple[str, str]]]:
    if name not in DESIGNS:
        raise ValueError(f"Design '{name}' is not defined.")
    return DESIGNS[name](participant_ids, item_ids, conditions)


@_register
def full_crossing(
    participant_ids: list[str], item_ids: list[str], conditions: list[str]
) -> dict[str, list[tuple[str, str]]]:
    """
    Every participant sees every item in every condition.
    """
    design = {}
    for participant_id in participant_ids:
        design[participant_id] = []
        for item_id in item_ids:
            for condition in conditions:
                design[participant_id].append((item_id, condition))
    return design


@_register
def latin_square(
    participant_ids: list[str], item_ids: list[str], conditions: list[str]
) -> dict[str, list[tuple[str, str]]]:
    """
    Every participant sees every item in exactly one condition,
    and every condition is seen equally often across participants and items.
    """
    if len(participant_ids) % len(conditions) != 0:
        warnings.warn(
            f"Number of participants ({len(participant_ids)}) is not a multiple "
            f"of the number of conditions ({len(conditions)}). "
            f"This will lead to an unbalanced design."
        )
    if len(item_ids) % len(conditions) != 0:
        warnings.warn(
            f"Number of items ({len(item_ids)}) is not a multiple "
            f"of the number of conditions ({len(conditions)}). "
            f"This will lead to an unbalanced design."
        )

    # Create as many item lists as there are conditions
    item_lists = []
    for list_index in range(len(conditions)):
        item_list = []
        for item_index, item_id in enumerate(item_ids):
            # Rotate condition based on item and list index
            condition_index = (item_index + list_index) % len(conditions)
            condition = conditions[condition_index]
            item_list.append((item_id, condition))
        item_lists.append(item_list)

    # Assign item lists to participants
    design = {}
    for participant_index, participant_id in enumerate(participant_ids):
        list_index = participant_index % len(item_lists)
        design[participant_id] = item_lists[list_index].copy()

    return design
