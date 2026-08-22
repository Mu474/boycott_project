from rest_framework import serializers
from .models import BusinessEntity
from categories.serializers import CategorySerializer


class EntityMinimalSerializer(serializers.ModelSerializer):
    """نسخة مختصرة من الجهة، تُستخدم داخل المنتجات والجهات التابعة"""
    class Meta:
        model = BusinessEntity
        fields = ['id', 'name', 'logo', 'status']


class EntitySerializer(serializers.ModelSerializer):
    """تُستخدم عند الإنشاء والتعديل (POST/PUT) — حقول مسطّحة (IDs مباشرة)"""
    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'logo', 'status', 'reason',
            'evidence_url', 'category', 'parent_entity', 'created_at'
        ]

    def validate(self, data):
        """
        يمنع تكوين حلقة دائرية في التسلسل الهرمي عند تعيين parent_entity:
        - جهة لا يمكن أن تكون أبًا لنفسها.
        - جهة لا يمكن أن يكون "أبها" أحد أبنائها أو أحفادها (بأي عمق)،
          لأن هذا يخلق حلقة تدور بلا نهاية (مشكلة حقيقية لدالة
          cascade_status ولاحقًا لأي عرض شجري في الواجهة).
        هذا التحقق يعمل فقط عند التعديل (PUT) لأن الحلقة تتطلب وجود
        الجهة أصلًا بقاعدة البيانات؛ عند الإنشاء (POST) لا وجود لها بعد.
        """
        parent = data.get('parent_entity')
        instance = self.instance

        if parent is None or instance is None:
            return data

        if parent.id == instance.id:
            raise serializers.ValidationError(
                {'parent_entity': 'لا يمكن أن تكون الجهة أبًا لنفسها.'}
            )

        current = parent
        visited = set()
        while current is not None:
            if current.id == instance.id:
                raise serializers.ValidationError(
                    {'parent_entity': 'لا يمكن تعيين جهة تابعة (أو تابعة لها) كأب — هذا يكوّن حلقة دائرية في التسلسل الهرمي.'}
                )
            if current.id in visited:
                # حلقة موجودة مسبقًا بالبيانات من مصدر آخر (استيراد قديم
                # مثلًا) — لا نكرر المرور بها هنا، هذا خارج نطاق هذا التحقق
                break
            visited.add(current.id)
            current = current.parent_entity

        return data


class EntityDetailSerializer(serializers.ModelSerializer):
    """تُستخدم عند العرض (GET) — التصنيف والجهة المالكة متداخلان بالاسم الكامل"""
    category = CategorySerializer(read_only=True)
    parent_entity = EntityMinimalSerializer(read_only=True)

    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'logo', 'status', 'reason',
            'evidence_url', 'category', 'parent_entity', 'created_at'
        ]