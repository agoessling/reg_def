"""Create register definition files from target descriptions."""

_DEFINITIONS = {
    "ti": "--ti_xml",
}

def register_definition(name, out, definition_type, definition_file, data = [], **kwargs):
    """Create register definition file.

    Args:
        name: name of resulting cc_library target.
        out: name of resulting .h header file.
        definition_type: string specifying type of definition file.
        definition_file: definition file to be parsed.
        data: any extra files that need to be present during generation.
        **kwargs: other arguments passed to the resulting cc_library.
    """
    if definition_type not in _DEFINITIONS:
        msg = "Definition type \"{}\" not in: {}".format(definition_type, _DEFINITIONS.keys())
        fail(msg)
    def_arg = _DEFINITIONS[definition_type]

    native.genrule(
        name = name + "_gen",
        srcs = [definition_file] + data,
        outs = [out],
        cmd = "$(execpath @reg_def//src:reg_def) {} $(rootpath {}) --output $@".format(
            def_arg,
            definition_file,
        ),
        tools = ["@reg_def//src:reg_def"],
    )

    native.cc_library(
        name = name,
        hdrs = [out],
        **kwargs
    )

def rust_register_definition(name, definition_file, data = [], out = None, **kwargs):
    """Generate a Rust source file containing layout-only register definitions.

    The output can be included from a no_std Rust crate using compile_data and
    rustc_env. This rule intentionally does not create a Rust library or require
    consumers to use a particular rules_rust version.

    Args:
        name: Name of the generated source target.
        definition_file: TI device XML label.
        data: Peripheral XML files referenced by definition_file.
        out: Output filename; defaults to name + ".rs".
        **kwargs: Other arguments passed to genrule, such as visibility.
    """
    generator = Label("//src:reg_def")
    native.genrule(
        name = name,
        srcs = [definition_file] + data,
        outs = [out or name + ".rs"],
        cmd = "$(execpath {}) --language rust --ti_xml $(execpath {}) --output $@".format(
            generator,
            definition_file,
        ),
        tools = [generator],
        **kwargs
    )
