from django.db import models

# Create your models here.
# 1. user_login - id, user_id, uname, passwd, u_type, status
class user_login(models.Model):
    id = models.AutoField(primary_key=True)
    uname = models.CharField(max_length=100)
    passwd = models.CharField(max_length=25)
    u_type = models.CharField(max_length=10)
    status = models.CharField(max_length=10)
    def __str__(self):
        return self.uname

# 2. user_details - id, fname, lname, dob, gender, addr, email, contact, status
class user_details(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=200)
    gender = models.CharField(max_length=25)
    age = models.CharField(max_length=25)
    addr = models.CharField(max_length=500)
    pin = models.CharField(max_length=25)
    contact = models.CharField(max_length=25)
    email = models.CharField(max_length=150)
    status = models.CharField(max_length=10)
    def __str__(self):
        return self.fname


# 3. storage_details - id, user_id, total, used, status
class storage_details(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    total = models.CharField(max_length=25)
    used = models.CharField(max_length=25)
    status = models.CharField(max_length=25)

# 4. file_index - id, fname, file_size, dt, tm, signature, url, status
class file_index(models.Model):
    id = models.AutoField(primary_key=True)
    fname = models.CharField(max_length=25)
    file_size = models.CharField(max_length=25)
    dt = models.CharField(max_length=25)
    tm = models.CharField(max_length=25)
    signature = models.CharField(max_length=1000)
    url = models.CharField(max_length=150)
    status = models.CharField(max_length=25)

# 5. user_file_map - id, file_id, file_name, user_id, dt, tm, status
class user_file_map(models.Model):
    id = models.AutoField(primary_key=True)
    file_id = models.IntegerField()
    file_name = models.CharField(max_length=250)
    user_id = models.IntegerField()
    dt = models.CharField(max_length=25)
    tm = models.CharField(max_length=25)
    status = models.CharField(max_length=25)

# 6. feedback - id, user_id, msg, dt, tm, status
class feedback(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    msg = models.CharField(max_length=250)
    dt = models.CharField(max_length=25)
    tm = models.CharField(max_length=25)
    status = models.CharField(max_length=10)
    
# 7. support_ticket - For handling user support requests
class support_ticket(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=100, null=True, blank=True)
    user_email = models.CharField(max_length=150, null=True, blank=True)
    issue_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20)  # low, medium, high
    status = models.CharField(max_length=20, default='open')  # open, in-progress, resolved
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Ticket #{self.id}: {self.subject}"

# 8. notification - For user notifications about ticket status
class notification(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    ticket_id = models.IntegerField(null=True,blank=True)
    message = models.CharField(max_length=500)
    status = models.CharField(max_length=20, default='unread')  # unread, read
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification for User {self.user_id}: {self.message[:30]}"

# 9. shared_link - For file sharing between users
class SharedLink(models.Model):
    id = models.AutoField(primary_key=True)
    file = models.ForeignKey(file_index, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(user_login, on_delete=models.CASCADE, related_name='shared_by_user')
    shared_with_user = models.ForeignKey(user_login, on_delete=models.CASCADE, related_name='shared_with_user', null=True, blank=True)
    shared_with_email = models.CharField(max_length=200, blank=True, null=True)
    
    # Unique token for the share link
    token = models.CharField(max_length=100, unique=True)
    
    # Expiration settings
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Permissions
    can_download = models.BooleanField(default=True)
    can_view = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    accessed_at = models.DateTimeField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'myapp_shared_link'
    
    def __str__(self):
        return f"Share: {self.file.fname} from {self.shared_by.uname} to {self.shared_with_user.uname if self.shared_with_user else self.shared_with_email}"
    
    def is_expired(self):
        """Check if share link has expired"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False