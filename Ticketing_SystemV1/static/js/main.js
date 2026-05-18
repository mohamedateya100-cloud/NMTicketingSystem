// الكود النووي لمنع الاقتراحات ومدير الباسووردات من التدخل في السيستم
document.addEventListener('DOMContentLoaded', function() {
    
    // 1. نقفل الفورم نفسها
    document.querySelectorAll('form').forEach(function(form) {
        form.setAttribute('autocomplete', 'off');
    });

    // 2. لفة على كل الخانات اللي في السيستم
    document.querySelectorAll('input').forEach(function(input) {
        // بنحط 'new-password' حتى لخانات النص عشان نخدع المتصفح ونقفل قايمة الباسووردات
        input.setAttribute('autocomplete', 'new-password');
        
        // الكود ده بيقفل إضافات المتصفح الخارجية لو بتستخدم حاجة زي LastPass أو 1Password
        input.setAttribute('data-lpignore', 'true');
        
        // خدعة إضافية: بنخلي المتصفح يفتكر الخانة للقراءة فقط أجزاء من الثانية عشان يفقد الأمل فيها
        if (input.type === 'password' || input.type === 'email') {
            input.setAttribute('readonly', 'readonly');
            setTimeout(function() {
                input.removeAttribute('readonly');
            }, 50);
        }
    });
});