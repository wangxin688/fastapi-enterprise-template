import re
from typing import Any, TypeVar
from unicodedata import normalize

_T = TypeVar("_T", str, int, float)
_pruntutaion_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
MAC_ADDRESS_LENGTH = 12


def mac_address_validator(mac: str) -> str:
    """
    Validates the given MAC address.

    Args:
        mac (str): The MAC address to be validated.

    Returns:
        str: The validated MAC address in colon-separated format.

    Raises:
        ValueError: If the MAC address is not in the correct format.
    """
    _mac_address_re = r"^[0-9a-fA-F]{12}$"
    input_mac = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(mac) != MAC_ADDRESS_LENGTH:
        raise ValueError("validation_error.bad_mac_format")
    if re.match(_mac_address_re, input_mac):
        return ":".join(input_mac[i : i + 2] for i in range(0, len(input_mac), 2)).lower()
    raise ValueError("validation_error.bad_mac_format")


def items_to_list(values: _T | list[_T]) -> list[_T]:
    """
    Convert the input values to a list. If the input is a single value, it will be
    wrapped in a list. If the input is already a list, it will be returned as is.

    :param values: Either a single value or a list of values
    :type values: Union[int, str, float, List[Union[int, str, float]]]
    :return: A list of values
    :rtype: List[Union[int, str, float]]
    """
    if isinstance(values, int | str | float):
        return [values]
    return values


def slugify(text: str, delim: str = "-") -> str:
    """
    Generate a slug from the given text using the specified delimiter.

    Args:
        text: A string to be slugified.
        delim: A string to be used as the delimiter. Defaults to "-".

    Returns:
        A slugified string.
    """
    result = [
        normalize("NFKD", word).encode("ascii", "ignore").decode("utf-8")
        for word in re.split(r"\W+", text.lower())
        if word
    ]
    return delim.join(result)


def list_to_tree(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert a list of nodes into a tree structure.

    Args:
        nodes (list[dict[str, Any]]): A list of dictionaries representing nodes.

    Returns:
        list[dict[str, Any]]: A list of dictionaries representing the tree structure.
    """
    node_dict = {node["id"]: node for node in nodes}
    tree: list[dict[str, Any]] = []

    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is None:
            tree.append(node)
        else:
            parent_node = node_dict.get(parent_id)
            if parent_node is not None:
                parent_node.setdefault("children", []).append(node)

    return tree


def tree_to_list(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert a tree represented as a list of dictionaries into a list of dictionaries.

    Args:
        tree (list[dict[str, Any]]): The input tree to be converted.

    Returns:
        list[dict[str, Any]]: The resulting list after converting the tree.
    """
    result: list[dict[str, Any]] = []

    def dfs(node: dict[str, Any]) -> None:
        result.append(node)
        children = node.get("children", [])
        for child in children:
            dfs(child)

    for node in tree:
        dfs(node)

    return result
