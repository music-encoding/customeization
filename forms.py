import conf
from flask_wtf import Form
from wtforms import RadioField, FileField, SelectField, BooleanField
from wtforms.validators import InputRequired


class ProcessForm(Form):
    SOURCE_OPTIONS = [('schema-2013', "MEI 2013 (v{0})".format(conf.LATEST_TAG_2013)),
                      ('schema-2012', "MEI 2012 (v{0})".format(conf.LATEST_TAG_2012)),
                      ('schema-latest', 'Latest from Development Branch'),
                      ('local-source', "Local Canonicalized Driver File")]

    CUSTOMIZATION_OPTIONS = [(k, conf.AVAILABLE_CUSTOMIZATIONS[k][0]) for k in sorted(conf.AVAILABLE_CUSTOMIZATIONS)]

    schema_language = SelectField(u'Schema Language',
                                 choices=[('relaxng', 'RelaxNG Schema'),
                                          ('compiledodd', 'Compiled ODD'),
                                          ('documentation', 'HTML Documentation')],
                                 validators=[InputRequired()])

    source_options = SelectField(u'MEI Source',
                                choices=SOURCE_OPTIONS,
                                validators=[InputRequired()])

    source_canonical_file = FileField(u"Canonicalized Driver File")

    customization_options = SelectField(u"MEI Customization",
                                        choices=CUSTOMIZATION_OPTIONS,
                                        validators=[InputRequired()])

    local_customization_file = FileField(u"Customization File")

    verbose_output = BooleanField(u'Verbose output')
