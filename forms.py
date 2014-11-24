import conf
from flask_wtf import Form
from wtforms import RadioField, FileField
from wtforms.validators import InputRequired, DataRequired, ValidationError


class ProcessForm(Form):
    SOURCE_OPTIONS = [('schema-2013', "MEI 2013 (v{0})".format(conf.LATEST_TAG_2013)),
                      ('schema-2012', "MEI 2012 (v{0})".format(conf.LATEST_TAG_2012)),
                      ('schema-latest', 'Latest from Development Branch'),
                      ('local-source', "Local Canonicalized Driver File")]

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

    source_canonical_file = FileField(u"Canonicalized Driver File")

    customization_options = RadioField(u'MEI Customization',
                                       choices=CUSTOMIZATION_OPTIONS,
                                       validators=[InputRequired()])

    local_customization_file = FileField(u"Customization File")
