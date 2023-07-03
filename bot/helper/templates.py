from bot.helper.datetime import format_iso_time
import jinja2


JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader("bot/modules/"))
JINJA_ENV.filters['format_iso_time'] = format_iso_time


def render_response_template(path, *args, **kwargs) -> str:
    """
    Render the HTML templates for use in telegram. Add supports for 2 additional tags: <p></p> and <br> or <br/>

    Parameters
    ----------
    path : str
        path to html file from root(./bot/modules)

    *args
        passed to jinja2 template render function
    **kwargs
        passed to jinja2 template render function

    Returns
    -------
    str:
        rendered text for telegram bot api
    """

    template = JINJA_ENV.get_template(path)
    html = template.render(*args, **kwargs)

    html_processed = ""
    preformatted_section = False
    for line in html.splitlines():

        line_stripped = line.strip()

        if line_stripped.startswith("<pre>"):
            preformatted_section = True

        if preformatted_section == True:
            if "</pre>" in line_stripped:
                preformatted_section = False
                html_processed += line
                continue

            html_processed += line + "\n"
            continue

        line_stripped = line_stripped.replace('<p>', "")
        line_stripped = line_stripped.replace('</p>', "\n\n")
        line_stripped = line_stripped.replace('<br>', "\n")
        line_stripped = line_stripped.replace('<br/>', "\n")

        html_processed += line_stripped

    return html_processed
