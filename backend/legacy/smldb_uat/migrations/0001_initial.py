from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TEmailLog',
            fields=[
                ('email_log_id', models.AutoField(db_column='email_log_id', primary_key=True, serialize=False)),
                ('reference_client_id', models.CharField(db_column='REFERENCE_CLIENT_ID', max_length=100, null=True)),
                ('email_id', models.CharField(db_column='EMAIL_ID', max_length=100, null=True)),
                ('responce_code', models.CharField(db_column='RESPONCE_CODE', max_length=100, null=True)),
                ('client_type', models.CharField(db_column='CLIENT_TYPE', max_length=100, null=True)),
                ('request_ref_id', models.CharField(db_column='REQUEST_REF_ID', max_length=100, null=True)),
                ('responce_message', models.CharField(db_column='RESPONCE_MESSAGE', max_length=100, null=True)),
                ('delivery_report', models.CharField(db_column='DELIVERY_REPORT', max_length=100, null=True)),
                ('send_date', models.DateTimeField(db_column='SEND_DATE', null=True)),
                ('reftxid', models.CharField(db_column='REFTXID', max_length=100, null=True)),
                ('project_id', models.IntegerField(db_column='PROJECT_ID', null=True)),
                ('server_ip_address', models.CharField(db_column='SERVER_IP_ADDRESS', max_length=100, null=True)),
                ('msg_send_status', models.IntegerField(db_column='MSG_SEND_STATUS', null=True)),
                ('email_from', models.CharField(db_column='EMAIL_FROM', max_length=100, null=True)),
                ('subject', models.CharField(db_column='SUBJECT', max_length=100, null=True)),
                ('attachement_path', models.CharField(db_column='ATTACHEMENT_PATH', max_length=500, null=True)),
                ('attach_file_type', models.CharField(db_column='ATTACH_FILE_TYPE', max_length=100, null=True)),
                ('message_id', models.CharField(db_column='MESSAGE_ID', max_length=100, null=True)),
                ('tracking_id', models.CharField(db_column='TRACKING_ID', max_length=100, null=True)),
                ('message', models.CharField(db_column='MESSAGE', max_length=2000, null=True)),
            ],
            options={
                'db_table': 'email_log',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TSmsLog',
            fields=[
                ('sms_log_id', models.AutoField(db_column='SMS_LOG_ID', primary_key=True, serialize=False)),
                ('reference_client_id', models.CharField(db_column='REFERENCE_CLIENT_ID', max_length=100, null=True)),
                ('mobile_no', models.CharField(db_column='MOBILE_NO', max_length=100, null=True)),
                ('message', models.CharField(db_column='MESSAGE', max_length=2000, null=True)),
                ('responce_code', models.CharField(db_column='RESPONCE_CODE', max_length=100, null=True)),
                ('senderid', models.CharField(db_column='SENDERID', max_length=100, null=True)),
                ('client_type', models.CharField(db_column='CLIENT_TYPE', max_length=100, null=True)),
                ('request_ref_id', models.CharField(db_column='REQUEST_REF_ID', max_length=100, null=True)),
                ('responce_message', models.CharField(db_column='RESPONCE_MESSAGE', max_length=2000, null=True)),
                ('delivery_report', models.CharField(db_column='DELIVERY_REPORT', max_length=100, null=True)),
                ('send_date', models.DateTimeField(db_column='SEND_DATE', null=True)),
                ('reftxid', models.CharField(db_column='REFTXID', max_length=100, null=True)),
                ('server_ip_address', models.CharField(db_column='SERVER_IP_ADDRESS', max_length=100, null=True)),
                ('is_otp', models.IntegerField(db_column='IS_OTP', null=True)),
                ('template_id', models.CharField(db_column='TEMPLATE_ID', max_length=100, null=True)),
                ('record_id', models.IntegerField(db_column='RECORD_ID', null=True)),
                ('msg_send_status', models.IntegerField(db_column='MSG_SEND_STATUS', null=True)),
                ('projectid', models.IntegerField(db_column='PROJECTID', null=True)),
            ],
            options={
                'db_table': 'sms_log',
                'managed': False,
            },
        ),
    ]
