from flask_wtf import Form
from wtforms import RadioField
from wtforms.validators import DataRequired


class ProcessForm(Form):
    schema_language = RadioField('Schema Language', choices=[('relaxng', 'RelaxNG'), ('compiledodd', 'Compiled ODD')])
    source_options = RadioField('MEI Source', choices=[('schema-2013', "MEI 2013 (v2.1.0)"),
                                                       ('schema-2012', "MEI 2012 (v2.0.0)"),
                                                       ('schema-latest', 'Latest from Development Branch'),
                                                       ('localsource', "Local Canonicalized Driver File")])
    customization_options = RadioField('MEI Customization', choices=[('meiall-2013', "MEI All from MEI 2013"),
                                                                     ('meiall-2012', "MEI All from MEI 2012"),
                                                                     ('meiall-develop', "MEI All from Development Branch"),
                                                                     ('local-customization', "Local Customization File")])