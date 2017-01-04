from docutils import nodes
import sys

def dropdown_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Role to create dropdown list of URLs for html only.

    e.g.

    :dropdown:`menu-title, [link1](url1), [link2](url2), [link3](url3), ...`

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """

    title, items = text.split(',')[0], text.split(',')[1:]

    dropdown_html = STYLE + OPEN.replace('TITLE', title)

    print items
    for item in items:

        # Check if link is formatted correctly
        if item.find('[') == -1 or item.find(']') == -1 or \
           item.find('(') == -1 or item.find(')') == -1:

            sys.stderr.write('Malformed dropdown role link\n')
            raise AttributeError

        # Get url & linktext
        url = item[item.find('(')+1:item.find(')')]
        linktext = item[item.find('[')+1:item.find(']')]

        item_html = LINK.replace('LINKTEXT', linktext)
        item_html = item_html.replace('URL', url)
        dropdown_html += item_html + '\n'

    dropdown_html += CLOSE

    node = nodes.raw('', dropdown_html, format='html')
    return [node], []

LINK = '<li><a href="URL">LINKTEXT</a></li>'

OPEN = """
    <nav role="navigation">
    <ul class="access-menu">
            <li>
                    <a href="#">TITLE</a>
                    <ul class="access-submenu">
       """

CLOSE = """
                    </ul>
            </li>
    </ul>
    </nav>
    """

STYLE = """
<style>

    nav ul{
            list-style: none;
            margin: 0;
            padding: 0;
    }

    .access-menu{
            display: table;
    }

    .access-menu > li{
            background: #343131;
            display: inline-block;
            position: relative;
    }

    .access-menu > li + li{
            border-left: solid 1px #000;
    }

    .access-menu > li:hover .access-submenu{
            top: 100%;
            left: auto;
    }

    .access-menu a{
            color: #B3B3B3;
            display: block;
            padding: .5em 2em;
            text-decoration: none;
            transition: all .2s linear;
    }

    .access-menu a:hover,
    .access-menu a:focus{
            background: #369;
            outline: none;
    }

    .access-submenu{
            background: #343131;
            left: -9999px;
            position: absolute;
            top: -9999px;
            width: 125%;
    }

    .access-menu li{
        margin-left: 0px !important;
    }

    .access-submenu > li + li{
            border-top: solid 1px #000;
    }

    .access-submenu > li:last-child{
            border-bottom: solid 3px #000;
    }

    .access-submenu a{
            padding: .5em 1em;
    }

    .is-show{
            left: auto;
            top: 100%;
    }

    </style>
    """


def setup(app):
    app.add_role('dropdown', dropdown_role)
