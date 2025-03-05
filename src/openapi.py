from enum import Enum

from fastapi.responses import HTMLResponse


class TryItCredentialPolicyOptions(Enum):
    OMIT = "omit"
    include = "include"
    SAME_ORIGIN = "same-origin"


class LayoutOptions(Enum):
    SIDEBAR = "sidebar"
    STACKED = "stacked"


class RouterOptions(Enum):
    HISTORY = "history"
    HASH = "hash"
    MEMORY = "memory"
    STATIC = "static"


def get_stoplight_elements_html(
    *,
    openapi_url: str,
    title: str,
    stoplight_elements_js_url: str = "https://unpkg.com/@stoplight/elements/web-components.min.js",
    stoplight_elements_css_url: str = "https://unpkg.com/@stoplight/elements/styles.min.css",
    stoplight_elements_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    api_description_document: str = "",
    base_path: str = "",
    hide_internal: bool = False,
    hide_try_it: bool = False,
    try_it_cors_proxy: str = "",
    try_it_credential_policy: TryItCredentialPolicyOptions = TryItCredentialPolicyOptions.OMIT,
    layout: LayoutOptions = LayoutOptions.SIDEBAR,
    logo: str = "",
    router: RouterOptions = RouterOptions.HISTORY,
) -> HTMLResponse:
    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>{title}</title>
        <link rel="shortcut icon" href="{stoplight_elements_favicon_url}">
        <script src="{stoplight_elements_js_url}"></script>
        <link rel="stylesheet" href="{stoplight_elements_css_url}">
    </head>
    <body>
        <elements-api
            {f'apiDescriptionUrl="{openapi_url}"' if openapi_url != "" else ""}
            {f'apiDescriptionDocument="{api_description_document}"' if api_description_document != "" else ""}
            {f'basePath="{base_path}"' if base_path != "" else ""}
            {'hideInternal="true"' if hide_internal is True else ""}
            {'hideTryIt="true"' if hide_try_it is True else ""}
            {f'tryItCorsProxy="{try_it_cors_proxy}"' if try_it_cors_proxy != "" else ""}
            tryItCredentialPolicy="{try_it_credential_policy.value}"
            layout="{layout.value}"
            {f'logo="{logo}"' if logo != "" else ""}
            router="{router.value}"
        />
    </body>
    </html>
    """
    return HTMLResponse(html)


def get_open_api_intro() -> str: ...
