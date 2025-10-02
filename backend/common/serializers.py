from .models import File
from rest_framework import serializers


class FileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ['id', 'name', 'file_url']

    def get_file_url(self, file_obj):
        request = self.context.get('request')
        if request and file_obj.file:
            return request.build_absolute_uri(file_obj.file.url)
        return None