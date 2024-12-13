{
    'name': 'Employee Resignation',
    'version': '17.0.1.0.0',
    'summary': 'Handle Employee Resignation Process',
    'author': "Tiju's Academy",
    'depends': ['base', 'web', 'mail', 'hr'],
    'data': [
        'data/ir_sequence.xml',
        'data/activity.xml',
        'security/groups.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/resignation_type_view.xml',
        'views/resignation_view.xml',
        'views/resignation_menu.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}