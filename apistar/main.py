import os
import shutil

import click
import jinja2

import apistar
from apistar.exceptions import ParseError, ValidationError
from apistar.schemas import OpenAPI, Swagger
from apistar.validate import validate as apistar_validate


def static_url(filename):
    return filename


@click.group()
def main():
    pass


def _base_format_from_filename(filename):
    base, extension = os.path.splitext(filename)
    return {
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml'
    }.get(extension)


def _echo_error(exc, verbose=False):
    if verbose:
        # Verbose output style.
        lines = content.splitlines()
        for message in reversed(exc.messages):
            error_str = ' ' * (message.position.column_no - 1)
            error_str += '^ '
            error_str += message.text
            error_str = click.style(error_str, fg='red')
            lines.insert(message.position.line_no, error_str)
        for line in lines:
            click.echo(line)

        click.echo()
    else:
        # Compact output style.
        for message in exc.messages:
            pos = message.position
            if message.code == 'required':
                index = message.index[:-1]
            else:
                index = message.index
            if index:
                fmt = '* %s (At %s, line %d, column %d.)'
                output = fmt % (message.text, index, pos.line_no, pos.column_no)
                click.echo(output)
            else:
                fmt = '* %s (At line %d, column %d.)'
                output = fmt % (message.text, pos.line_no, pos.column_no)
                click.echo(output)

    click.echo(click.style('✘ ', fg='red') + exc.summary)


FORMAT_SCHEMA_CHOICES = click.Choice(['openapi', 'swagger'])
FORMAT_ALL_CHOICES = click.Choice(['json', 'yaml', 'config', 'jsonschema', 'openapi', 'swagger'])
BASE_FORMAT_CHOICES = click.Choice(['json', 'yaml'])


@click.command()
@click.argument('schema', type=click.File('rb'))
@click.option('--format', type=FORMAT_ALL_CHOICES, required=True)
@click.option('--base-format', type=BASE_FORMAT_CHOICES, default=None)
@click.option('--verbose', '-v', is_flag=True, default=False)
def validate(schema, format, base_format, verbose):
    content = schema.read()
    if base_format is None:
        base_format = _base_format_from_filename(schema.name)

    try:
        value = apistar_validate(content, format=format, base_format=base_format)
    except (ParseError, ValidationError) as exc:
        _echo_error(exc, verbose=verbose)
        return

    success_summary = {
        'json': 'Valid JSON',
        'yaml': 'Valid YAML',
        'config': 'Valid APIStar config.',
        'jsonschema': 'Valid JSONSchema document.',
        'openapi': 'Valid OpenAPI schema.',
        'swagger': 'Valid Swagger schema.',
    }[format]
    click.echo(click.style('✓ ', fg='green') + success_summary)


@click.command()
@click.argument('schema', type=click.File('rb'))
@click.option('--format', type=FORMAT_SCHEMA_CHOICES, required=True)
@click.option('--base-format', type=BASE_FORMAT_CHOICES, default=None)
@click.option('--verbose', '-v', is_flag=True, default=False)
def docs(schema, format, base_format, verbose):
    content = schema.read()
    if base_format is None:
        base_format = _base_format_from_filename(schema.name)

    try:
        value = apistar_validate(content, format=format, base_format=base_format)
    except (ParseError, ValidationError) as exc:
        _echo_error(exc, verbose=verbose)
        return

    decoder = {
        'openapi': OpenAPI,
        'swagger': Swagger
    }[format]
    document = decoder().load(value)

    loader = jinja2.PrefixLoader({
        'apistar': jinja2.PackageLoader('apistar', 'templates')
    })
    env = jinja2.Environment(autoescape=True, loader=loader)

    template = env.get_template('apistar/docs/index.html')
    code_style = None  # pygments_css('emacs')
    output_text = template.render(
        document=document,
        langs=['javascript', 'python'],
        code_style=code_style,
        static_url=static_url
    )

    directory = 'site'
    output_path = os.path.join(directory, 'index.html')
    if not os.path.exists(directory):
        os.makedirs(directory)
    output_file = open(output_path, 'w')
    output_file.write(output_text)
    output_file.close()

    static_dir = os.path.join(os.path.dirname(apistar.__file__), 'static')
    shutil.copytree(static_dir, os.path.join(directory, 'apistar'))

    click.echo('Documentation built at %s' % output_path)


main.add_command(docs)
main.add_command(validate)
