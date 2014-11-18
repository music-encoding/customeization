import conf
from flask_wtf import Form
from wtforms import RadioField, FileField
from wtforms.validators import InputRequired

# Source: http://stackoverflow.com/questions/8463209/how-to-make-a-field-conditionally-optional-in-wtforms
class RequiredIf(InputRequired):
    """
        Provides a validator for a field that is dependent on the value of another field in the form.
    """
    def __init__(self, other_field_name, value, *args, **kwargs):
        self.other_field_name = other_field_name
        self.value = value
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(u"No field named {0} in form".format(self.other_field_name))
        if other_field.data == self.value:
            super(RequiredIf, self).__call__(form, field)


class ProcessForm(Form):
    SOURCE_OPTIONS = [('schema-2013', "MEI 2013 (v{0})".format(conf.LATEST_TAG_2013)),
                      ('schema-2012', "MEI 2012 (v{0})".format(conf.LATEST_TAG_2012)),
                      ('schema-latest', 'Latest from Development Branch'),
                      ('localsource', "Local Canonicalized Driver File")]

    CUSTOMIZATION_OPTIONS = [('meiall-2013', "MEI All from MEI 2013"),
                             ('meiall-2012', "MEI All from MEI 2012"),
                             ('meiall-develop', "MEI All from Development Branch"),
                             ('local-customization', "Local Customization File")]

    schema_language = RadioField(u'Schema Language',
                                 choices=[('relaxng', 'RelaxNG'),
                                          ('compiledodd', 'Compiled ODD')],
                                 validators=[InputRequired()])

    source_options = RadioField(u'MEI Source',
                                choices=SOURCE_OPTIONS,
                                validators=[InputRequired()])

    source_canonical_file = FileField(u"Canonicalized Driver File",
                                      validators=[RequiredIf("source_options", "localsource")])

    customization_options = RadioField(u'MEI Customization',
                                       choices=CUSTOMIZATION_OPTIONS,
                                       validators=[InputRequired()])

    local_customization_file = FileField(u"Customization File",
                                         validators=[RequiredIf("customization_options", "local-customization")])
