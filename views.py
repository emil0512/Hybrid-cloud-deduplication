from django.shortcuts import render, redirect
from django.db.models import Max, Sum
from .models import user_login, user_details
from .models import storage_details, user_file_map, file_index
from datetime import datetime
from django.core.files.storage import FileSystemStorage
import os
from project.settings import BASE_DIR
from django.contrib import messages
from .models import support_ticket, notification, feedback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json
import hashlib
from .own_cloud import *
import logging
import uuid
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse
from .models import SharedLink  # Make sure SharedLink is imported
from .file_scanner import scan_file_content
logger = logging.getLogger(__name__)

def index(request):
    return render(request, './myapp/index.html')

def about(request):
    return render(request, './myapp/about.html')

# AJAX endpoint for username validation
def check_username(request):
    username = request.GET.get('username', '')
    exists = user_login.objects.filter(uname=username).exists()
    return JsonResponse({'exists': exists})

def contact(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        issue_type = request.POST.get('issue_type')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        priority = request.POST.get('priority')
        
        # Validate username exists
        try:
            user = user_login.objects.get(uname=username)
            user_id = user.id
            user_name = user.uname
            user_email = user_details.objects.get(user_id=user.id).email
        except user_login.DoesNotExist:
            messages.error(request, 'Invalid username! Please enter a valid registered username.')
            return render(request, './myapp/contact.html')
        except user_details.DoesNotExist:
            user_email = 'Not provided'
        
        # Save to support_ticket table
        ticket = support_ticket(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            issue_type=issue_type,
            subject=subject,
            message=message,
            priority=priority,
            status='open'
        )
        ticket.save()
        
        # Create notification for admin
        notif = notification(
            user_id=user_id,
            ticket_id=ticket.id,
            message=f'New support ticket #{ticket.id} created with {priority} priority',
            status='unread'
        )
        notif.save()
        
        # Show success message
        messages.success(request, f'Support request sent! Admin will respond within 24-48 hours.')
        
        return render(request, './myapp/contact.html')
    
    else:
        return render(request, './myapp/contact.html')

#################### ADMIN ##################################
def admin_login(request):
    if request.method == 'POST':
        un = request.POST.get('un')
        pwd = request.POST.get('pwd')
        
        ul = user_login.objects.filter(uname=un, passwd=pwd, u_type='admin')

        if len(ul) == 1:
            # Clear any existing session first
            request.session.flush()
            
            # Set new session
            request.session['user_name'] = ul[0].uname
            request.session['user_id'] = ul[0].id
            request.session['login_time'] = str(datetime.now())
            request.session.set_expiry(3600)  # Session expires after 1 hour
            
            return redirect('admin_home')
        else:
            msg = '<h1> Invalid Uname or Password !!!</h1>'
            context ={ 'msg1':msg }
            return render(request, './myapp/admin_login.html', context)
    else:
        # Check if this is a redirect from logout
        logout_msg = ''
        if request.GET.get('logout') == 'success':
            logout_msg = '<div class="alert alert-success">You have been logged out successfully!</div>'
        
        context ={ 'msg1': logout_msg }
        return render(request, './myapp/admin_login.html', context)


def admin_required(view_func):
    """Decorator to check if admin is logged in"""
    def wrapper(request, *args, **kwargs):
        if 'user_name' not in request.session or 'user_id' not in request.session:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_home(request):
    try:
        uname = request.session['user_name']
        print(uname)
        
        # Get dashboard statistics
        total_users = user_login.objects.filter(u_type='user').count()
        total_files = file_index.objects.count()
        
        # Calculate total storage used
        storage_total = storage_details.objects.aggregate(total_used=Sum('used'))['total_used'] or 0
        storage_used_gb = round(int(storage_total) / (1024**3), 2) if storage_total else 0
        
        open_tickets = support_ticket.objects.filter(status='open').count()
        new_feedback = feedback.objects.filter(status='ok').count()
        
        # Calculate storage percentage
        total_storage_capacity = 15 * 1073741824 * total_users if total_users > 0 else 1
        storage_percentage = round((int(storage_total) / total_storage_capacity) * 100, 1) if storage_total > 0 else 0
        
        context = {
            'total_users': total_users,
            'total_files': total_files,
            'storage_used': storage_used_gb,
            'storage_free': 100 - storage_percentage if storage_percentage else 100,
            'open_tickets': open_tickets,
            'new_feedback': new_feedback,
            'storage_percentage': storage_percentage,
        }
        
    except Exception as e:
        print(f"Error in admin_home: {e}")
        return redirect('admin_login')
    
    # Add cache control headers
    response = render(request, './myapp/admin_home.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


def admin_logout(request):
    try:
        request.session.flush()
    except:
        pass
    
    # Use reverse to generate the correct URL
    response = redirect(f"{reverse('admin_login')}?logout=success")
    
    # Prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@admin_required
def admin_changepassword(request):
    if request.method == 'POST':
        # Handle both regular POST and AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
        else:
            # Regular form submission
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
        
        uname = request.session.get('user_name')
        
        try:
            ul = user_login.objects.get(uname=uname, passwd=current_password, u_type='admin')
            ul.passwd = new_password
            ul.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Password changed successfully!'})
            else:
                messages.success(request, 'Password changed successfully!')
                return render(request, './myapp/admin_changepassword.html', {'msg': 'Password Changed'})
                
        except user_login.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Current password is incorrect!'}, status=400)
            else:
                messages.error(request, 'Current password is incorrect!')
                return render(request, './myapp/admin_changepassword.html', {'msg': 'Password Not Changed'})
    else:
        return render(request, './myapp/admin_changepassword.html', {'msg': ''})


@admin_required
def admin_user_view(request):
    ul_l = user_login.objects.filter(u_type='user')

    tm_l = []
    for u in ul_l:
        try:
            ud = user_details.objects.get(user_id=u.id)
            tm_l.append(ud)
        except user_details.DoesNotExist:
            pass

    context = {'user_list': tm_l, 'total_users': len(tm_l)}
    return render(request, './myapp/admin_user_view.html', context)


@admin_required
def admin_user_delete(request):
    id = request.GET.get('id')
    print("id="+id)

    try:
        nm = user_details.objects.get(id=int(id))
        u_l = user_login.objects.get(id=nm.user_id)
        
        # Delete user's files and storage
        user_files = user_file_map.objects.filter(user_id=nm.user_id)
        for uf in user_files:
            try:
                fi = file_index.objects.get(id=uf.file_id)
                fi.delete()
            except:
                pass
        user_files.delete()
        
        # Delete storage details
        storage_details.objects.filter(user_id=nm.user_id).delete()
        
        # Delete user feedback
        feedback.objects.filter(user_id=nm.user_id).delete()
        
        # Delete user tickets and notifications
        support_ticket.objects.filter(user_id=nm.user_id).delete()
        notification.objects.filter(user_id=nm.user_id).delete()
        
        u_l.delete()
        nm.delete()
        
        messages.success(request, 'User and all associated data deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return admin_user_view(request)


@admin_required
def admin_user_feedback_view(request):
    nm_l = feedback.objects.all().order_by('-id')
    cmd = {}
    for nm in nm_l:
        try:
            ud = user_details.objects.get(user_id=nm.user_id)
            cmd[nm.user_id] = f'{ud.fname} {ud.lname}'
        except:
            cmd[nm.user_id] = 'Unknown User'

    context = {'message_list': nm_l, 'user_list': cmd, 'total_messages': len(nm_l)}
    return render(request, 'myapp/admin_user_feedback_view.html', context)


@admin_required
def admin_support_tickets_view(request):
    tickets = support_ticket.objects.all().order_by('-created_at')
    context = {'tickets': tickets}
    return render(request, 'myapp/admin_support_tickets.html', context)


@admin_required
def admin_ticket_update(request):
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_response', '')
        
        # Get the ticket
        try:
            ticket = support_ticket.objects.get(id=ticket_id)
            old_status = ticket.status
            ticket.status = new_status
            
            # Add admin response if provided
            if admin_response:
                ticket.admin_response = admin_response
                ticket.responded_at = datetime.now()
            
            ticket.save()
            
            # Create notification for the user
            notif_msg = f'Your support ticket #{ticket.id} status changed from {old_status} to {new_status}'
            if admin_response:
                notif_msg += f'. Admin response: {admin_response[:50]}...'
                
            notif = notification(
                user_id=ticket.user_id,
                ticket_id=ticket.id,
                message=notif_msg,
                status='unread'
            )
            notif.save()
            
            messages.success(request, f'Ticket #{ticket_id} updated to {new_status}')
        except Exception as e:
            messages.error(request, f'Error updating ticket: {str(e)}')
        
        return admin_support_tickets_view(request)
    return admin_support_tickets_view(request)


def get_ticket_count(request):
    try:
        count = support_ticket.objects.filter(status='open').count()
        return JsonResponse({'count': count})
    except:
        return JsonResponse({'count': 0})


def get_dashboard_stats(request):
    try:
        total_users = user_login.objects.filter(u_type='user').count()
        total_files = file_index.objects.count()
        
        # Calculate total storage used
        storage_total = storage_details.objects.aggregate(total_used=Sum('used'))['total_used'] or 0
        storage_used_gb = round(int(storage_total) / (1024**3), 2) if storage_total else 0
        
        open_tickets = support_ticket.objects.filter(status='open').count()
        new_feedback = feedback.objects.filter(status='ok').count()
        
        # Get recent activities (last 5)
        recent_activities = []
        
        # Recent users
        recent_users = user_login.objects.filter(u_type='user').order_by('-id')[:2]
        for user in recent_users:
            try:
                ud = user_details.objects.get(user_id=user.id)
                recent_activities.append({
                    'type': 'user',
                    'title': f'New user registered: {ud.fname} {ud.lname}',
                    'time': 'Recently',
                })
            except:
                pass
        
        # Recent files
        recent_files = user_file_map.objects.order_by('-id')[:2]
        for file in recent_files:
            recent_activities.append({
                'type': 'file',
                'title': f'File uploaded: {file.file_name}',
                'time': 'Recently',
            })
        
        # Recent tickets
        recent_tickets = support_ticket.objects.filter(status='open').order_by('-id')[:1]
        for ticket in recent_tickets:
            recent_activities.append({
                'type': 'ticket',
                'title': f'New support ticket #{ticket.id}',
                'time': 'Recently',
            })
        
        # Recent feedback
        recent_feedback = feedback.objects.order_by('-id')[:1]
        for fb in recent_feedback:
            recent_activities.append({
                'type': 'feedback',
                'title': 'New feedback received',
                'time': 'Recently',
            })
        
        return JsonResponse({
            'total_users': total_users,
            'total_files': total_files,
            'storage_used': storage_used_gb,
            'open_tickets': open_tickets,
            'new_feedback': new_feedback,
            'recent_activities': recent_activities[:5]
        })
        
    except Exception as e:
        print(f"Error in get_dashboard_stats: {e}")
        return JsonResponse({
            'total_users': 0,
            'total_files': 0,
            'storage_used': 0,
            'open_tickets': 0,
            'new_feedback': 0,
            'recent_activities': []
        })


@admin_required
def admin_notifications(request):
    try:
        notifications = notification.objects.filter(status='unread').order_by('-created_at')[:20]
        
        open_tickets_count = support_ticket.objects.filter(status='open').count()
        in_progress_count = support_ticket.objects.filter(status='in_progress').count()
        resolved_count = support_ticket.objects.filter(status='resolved').count()
        closed_count = support_ticket.objects.filter(status='closed').count()
        
        recent_feedback = feedback.objects.order_by('-id')[:5]
        
        context = {
            'notifications': notifications,
            'open_tickets_count': open_tickets_count,
            'in_progress_count': in_progress_count,
            'resolved_count': resolved_count,
            'closed_count': closed_count,
            'recent_feedback': recent_feedback
        }
        
        return render(request, 'myapp/admin_notifications.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading notifications: {str(e)}')
        return admin_home(request)


@admin_required
def admin_ticket_detail(request, ticket_id):
    try:
        ticket = support_ticket.objects.get(id=ticket_id)
        user_notifications = notification.objects.filter(ticket_id=ticket_id).order_by('-created_at')
        
        context = {
            'ticket': ticket,
            'notifications': user_notifications
        }
        return render(request, 'myapp/admin_ticket_detail.html', context)
        
    except support_ticket.DoesNotExist:
        messages.error(request, 'Ticket not found')
        return admin_support_tickets_view(request)


@csrf_exempt
def admin_bulk_ticket_update(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_ids = data.get('ticket_ids', [])
            new_status = data.get('status')
            
            updated_count = 0
            for ticket_id in ticket_ids:
                try:
                    ticket = support_ticket.objects.get(id=ticket_id)
                    old_status = ticket.status
                    ticket.status = new_status
                    ticket.save()
                    
                    notification.objects.create(
                        user_id=ticket.user_id,
                        ticket_id=ticket.id,
                        message=f'Your support ticket #{ticket.id} status changed from {old_status} to {new_status} (bulk update)',
                        status='unread'
                    )
                    updated_count += 1
                    
                except support_ticket.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'Updated {updated_count} tickets to {new_status}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


############################### USER ################################

def user_login_check(request):
    if request.method == 'POST':
        uname = request.POST.get('uname')
        passwd = request.POST.get('passwd')

        ul = user_login.objects.filter(uname=uname, passwd=passwd, u_type='user')
        print(len(ul))
        if len(ul) == 1:
            request.session['user_id'] = ul[0].id
            request.session['user_name'] = ul[0].uname
            
            # Get unread notification count
            notif_count = notification.objects.filter(user_id=ul[0].id, status='unread').count()
            
            context = {
                'uname': request.session['user_name'],
                'notif_count': notif_count
            }
            return render(request, 'myapp/user_home.html', context)
        else:
            context = {'msg': 'Invalid Credentials'}
            return render(request, 'myapp/user_login.html', context)
    else:
        return render(request, 'myapp/user_login.html')


def user_home(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    # Get files shared with this user
    shared_with_me = SharedLink.objects.filter(
        shared_with_user_id=user_id, 
        is_active=True
    ).select_related('shared_by', 'file')
    
    # Add file names to each share
    for share in shared_with_me:
        user_file = user_file_map.objects.filter(file_id=share.file.id).first()
        share.file_name = user_file.file_name if user_file else share.file.fname
    
    context = {
        'uname': request.session.get('user_name', ''),
        'shared_with_me': shared_with_me
    }
    return render(request, './myapp/user_home.html', context)


def user_details_add(request):
    if request.method == 'POST':
        fname = request.POST.get('fname')
        lname = request.POST.get('lname')
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        addr = request.POST.get('addr')
        pin = request.POST.get('pin')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        password = request.POST.get('pwd')
        uname = email
        status = "new"

        # Check if username already exists
        if user_login.objects.filter(uname=uname).exists():
            context = {'msg': 'Email already registered!'}
            return render(request, 'myapp/user_details_add.html', context)

        # Validate required fields
        if not fname or not lname or not email or not password:
            context = {'msg': 'Please fill in all required fields'}
            return render(request, 'myapp/user_details_add.html', context)

        # Basic email validation
        if '@' not in email or '.' not in email:
            context = {'msg': 'Please enter a valid email address'}
            return render(request, 'myapp/user_details_add.html', context)

        # Password length validation
        if len(password) < 6:
            context = {'msg': 'Password must be at least 6 characters long'}
            return render(request, 'myapp/user_details_add.html', context)

        ul = user_login(uname=uname, passwd=password, u_type='user', status=status)
        ul.save()
        user_id = user_login.objects.all().aggregate(Max('id'))['id__max']

        ud = user_details(
            user_id=user_id, fname=fname, lname=lname, gender=gender, 
            age=age, addr=addr, pin=pin, contact=contact, email=email
        )
        ud.save()

        sd = storage_details(user_id=user_id, total=str(15*1073741824), used='0', status='active')
        sd.save()

        # Welcome notification
        try:
            notification.objects.create(
                user_id=user_id,
                message='Welcome to HybridCloud! Start uploading your files.',
                status='unread',
            )
        except Exception as e:
            print(f"Could not create welcome notification: {e}")

        context = {'msg': 'User Registered Successfully! Please login.'}
        return render(request, 'myapp/user_login.html', context)

    else:
        return render(request, 'myapp/user_details_add.html')


def user_changepassword(request):
    if request.method == 'POST':
        uname = request.session['user_name']
        new_password = request.POST.get('new_password')
        current_password = request.POST.get('current_password')

        try:
            ul = user_login.objects.get(uname=uname, passwd=current_password, u_type='user')
            ul.passwd = new_password
            ul.save()
            
            # Remove the notification creation to avoid ticket_id error
            # Just show success message
            messages.success(request, 'Password Changed Successfully')
            return render(request, './myapp/user_changepassword.html', {'msg': 'Password Changed Successfully'})
            
        except user_login.DoesNotExist:
            messages.error(request, 'Current password is incorrect!')
            return render(request, './myapp/user_changepassword.html', {'msg': 'Password Not Changed'})
    else:
        return render(request, './myapp/user_changepassword.html')

def user_logout(request):
    try:
        del request.session['user_name']
        del request.session['user_id']
    except:
        pass
    return redirect('user_login')
def user_file_store_add(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            u_file = request.FILES['document']
            file_name = u_file.name
            user_id = int(request.session['user_id'])
            
            # Read file content from memory
            file_content = u_file.read()
            file_size = len(file_content)
            
            # ===== SCAN THE FILE =====
            threats = []
            is_safe = True
            
            try:
                from .file_scanner import scan_file_content
                is_safe, threats = scan_file_content(file_content, file_name)
            except ImportError:
                # Scanner not available, allow file
                is_safe = True
            except Exception as e:
                logger.error(f"Scan error: {str(e)}")
                is_safe = False
                threats = [f"Scanner error: {str(e)}"]
            
            # ===== IF NOT SAFE - REJECT =====
            if not is_safe:
                error_msg = "⛔ SECURITY ALERT: File Rejected!\n\n"
                error_msg += "The file was blocked because it contains malicious content.\n\n"
                error_msg += "🔴 Threats Detected:\n"
                for threat in threats:
                    error_msg += f"   • {threat}\n"
                error_msg += "\n📌 File was rejected for your security."
                
                if is_ajax:
                    return JsonResponse({
                        'success': False, 
                        'message': error_msg, 
                        'status': 'security_rejected'
                    })
                else:
                    return render(request, './myapp/user_file_store_add.html', {'msg': error_msg})
            
            # ===== FILE IS SAFE - SAVE =====
            # Compute hash
            import hashlib
            hasher = hashlib.md5()
            hasher.update(file_content)
            fsign = hasher.hexdigest()
            
            dt = datetime.today().strftime('%Y-%m-%d')
            tm = datetime.today().strftime('%H:%M:%S')
            
            # Save file to disk
            fs = FileSystemStorage()
            fpath = fs.save(file_name, u_file)
            
            url = f'testdir/{fpath}'
            
            file_obj = file_index.objects.filter(signature=fsign)
            is_new_file = len(file_obj) == 0
            file_status = 'new' if is_new_file else 'same'
            
            # Check storage limit
            s_d = storage_details.objects.get(user_id=user_id)
            current_used = int(s_d.used)
            total_limit = int(s_d.total)
            
            if current_used + file_size > total_limit:
                error_msg = '❌ Storage limit exceeded! Please free up some space.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg, 'status': 'limit_exceeded'})
                else:
                    return render(request, './myapp/user_file_store_add.html', {'msg': error_msg})
            
            # Save to database
            if is_new_file:
                file_i = file_index(
                    fname=fpath, file_size=file_size, signature=fsign,
                    dt=dt, tm=tm, url=url, status='notshared'
                )
                file_i.save()
                file_id = file_index.objects.all().aggregate(Max('id'))['id__max']
            else:
                file_id = file_obj[0].id
            
            ufm = user_file_map(
                file_id=file_id, file_name=file_name, user_id=user_id,
                dt=dt, tm=tm, status='notshared'
            )
            ufm.save()
                        # ===== UPLOAD TO OWNCLOUD =====
            if is_new_file:
                try:
                    target = url
                    src = os.path.join(BASE_DIR, f'myapp\\static\\myapp\\media\\{fpath}')
                    putfile(src=src, target=target)
                    print(f"OwnCloud upload successful: {target}")
                except Exception as e:
                    print(f"OwnCloud upload error: {e}")
            
            s_d.used = str(int(s_d.used) + int(file_size))
            s_d.save()
            
            success_msg = '✅ File Uploaded Successfully!'
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_msg,
                    'status': file_status,
                    'is_new': is_new_file,
                    'file_name': file_name,
                    'file_size': file_size
                })
            else:
                return render(request, './myapp/user_file_store_add.html', {'msg': success_msg})
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Upload error: {error_msg}")
            
            # Check if this was a security rejection
            if "security" in error_msg.lower() or "threat" in error_msg.lower():
                final_msg = "⛔ SECURITY ALERT: File rejected due to security concerns."
            else:
                final_msg = f"Upload failed: {error_msg}"
            
            if is_ajax:
                return JsonResponse({'success': False, 'message': final_msg})
            else:
                return render(request, './myapp/user_file_store_add.html', {'msg': final_msg})
    else:
        return render(request, './myapp/user_file_store_add.html')

def user_file_store_delete(request):
    id = request.GET.get('id')
    print('id = ' + id)
    
    try:
        ufm = user_file_map.objects.get(id=int(id))
        fi_o = file_index.objects.get(id=ufm.file_id)
        
        user_id = int(request.session['user_id'])
        s_d = storage_details.objects.get(user_id=user_id)
        s_d.used = str(int(s_d.used) - int(fi_o.file_size))
        s_d.save()
        
        ufm.delete()
        
        # Check if file is still referenced by other users
        other_refs = user_file_map.objects.filter(file_id=fi_o.id).count()
        if other_refs == 0:
            # Delete from cloud storage
            try:
                rmfile(src=fi_o.url)
            except:
                pass
            fi_o.delete()
            
        messages.success(request, 'File deleted successfully')
        
    except Exception as e:
        messages.error(request, f'Error deleting file: {str(e)}')
    
    return user_file_store_view(request)


def user_file_store_download(request):
    id = request.GET.get('id')
    print('id = ' + id)
    
    try:
        ufm = user_file_map.objects.get(id=int(id))
        fs = file_index.objects.get(id=int(ufm.file_id))
        
        #####################OWN Cloud Fetch#################################
        file_path = os.path.join(BASE_DIR, f'myapp\\static\\myapp\\media\\{fs.fname}')
        target = file_path
        src = fs.url
        getfile(src=src, target=target)
        ########################################################
        
        context = {'fileurl': fs.fname}
        return render(request, './myapp/user_file_store_download.html', context)
        
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return user_file_store_view(request)


def user_file_store_view(request):
    user_id = int(request.session['user_id'])
    fi_list = file_index.objects.all()
    ufm_l = user_file_map.objects.filter(user_id=user_id).order_by('-id')
    context = {'file_list': ufm_l, 'fi_list': fi_list}
    return render(request, './myapp/user_file_store_view.html', context)


def user_file_search(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        user_id = int(request.session['user_id'])

        fi_list = file_index.objects.all()
        ufm_l = user_file_map.objects.filter(user_id=user_id, file_name__icontains=query).order_by('-id')
        context = {'file_list': ufm_l, 'fi_list': fi_list, 'search_query': query}
        return render(request, './myapp/user_file_store_view.html', context)
    else:
        context = {}
        return render(request, './myapp/user_file_search.html', context)


def user_storage_view(request):
    user_id = int(request.session['user_id'])
    ufm_l = user_file_map.objects.filter(user_id=user_id)
    sd = storage_details.objects.get(user_id=user_id)
    
    total_bytes = int(sd.total)
    used_bytes = int(sd.used)
    free_bytes = total_bytes - used_bytes
    
    total_gb = round(total_bytes / (1024**3), 2)
    used_gb = round(used_bytes / (1024**3), 2)
    free_gb = round(free_bytes / (1024**3), 2)
    usage_percent = round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0
    
    context = {
        'sd': sd,
        'total': len(ufm_l),
        'total_gb': total_gb,
        'used_gb': used_gb,
        'free_gb': free_gb,
        'usage_percent': usage_percent,
        'free_space': str(free_bytes)
    }
    return render(request, './myapp/user_storage_view.html', context)


def user_details_update(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
        
    if request.method == 'POST':
        try:
            up = user_details.objects.get(user_id=int(user_id))

            up.fname = request.POST.get('fname')
            up.lname = request.POST.get('lname')
            up.gender = request.POST.get('gender')
            up.age = request.POST.get('dob')
            up.addr = request.POST.get('addr')
            up.pin = request.POST.get('pin')
            up.contact = request.POST.get('contact')
            up.email = request.POST.get('email')

            up.save()
            
            # Update username in login table if email changed
            user_login_obj = user_login.objects.get(id=user_id)
            if user_login_obj.uname != up.email:
                user_login_obj.uname = up.email
                user_login_obj.save()
                request.session['user_name'] = up.email

            messages.success(request, 'Profile Updated Successfully')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

        up = user_details.objects.get(user_id=int(user_id))
        context = {'up': up}
        return render(request, 'myapp/user_details_update.html', context)

    else:
        try:
            up = user_details.objects.get(user_id=int(user_id))
            context = {'up': up}
            return render(request, 'myapp/user_details_update.html', context)
        except user_details.DoesNotExist:
            messages.error(request, 'User details not found')
            return redirect('user_home')


def user_feedback_add(request):
    if request.method == 'POST':
        dt = datetime.today().strftime('%Y-%m-%d')
        tm = datetime.today().strftime('%H:%M:%S')
        msg = request.POST.get('msg')
        user_id = int(request.session['user_id'])
        
        # Validate message
        if not msg or not msg.strip():
            messages.error(request, 'Please enter a message before submitting.')
            return render(request, 'myapp/user_feedback_add.html', {'msg': 'Please enter a message'})
        
        # Save feedback
        fb = feedback(user_id=user_id, msg=msg, dt=dt, tm=tm, status='ok')
        fb.save()
        
        # Show success message (no notification to avoid ticket_id error)
        messages.success(request, 'Feedback posted successfully')
        
        context = {'msg': 'Feedback posted successfully'}
        return render(request, 'myapp/user_feedback_add.html', context)
    else:
        return render(request, 'myapp/user_feedback_add.html')

def user_feedback_delete(request):
    id = request.GET.get('id')
    print("id=" + id)

    try:
        nm = feedback.objects.get(id=int(id))
        nm.delete()
        messages.success(request, 'Feedback deleted successfully')
    except Exception as e:
        messages.error(request, f'Error deleting feedback: {str(e)}')
    
    return user_feedback_view(request)


def user_feedback_view(request):
    user_id = int(request.session['user_id'])
    nm_l = feedback.objects.filter(user_id=user_id).order_by('-id')
    cmd = {}
    for nm in nm_l:
        try:
            ud = user_details.objects.get(user_id=nm.user_id)
            cmd[nm.user_id] = f'{ud.fname} {ud.lname}'
        except:
            cmd[nm.user_id] = 'Unknown User'

    context = {'message_list': nm_l, 'user_list': cmd}
    return render(request, 'myapp/user_feedback_view.html', context)


# USER NOTIFICATIONS
def user_notifications(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    notifs = notification.objects.filter(user_id=user_id).order_by('-created_at')
    
    # Mark as read when viewed
    notifs.filter(status='unread').update(status='read')
    
    context = {'notifications': notifs}
    return render(request, 'myapp/user_notifications.html', context)


def user_notification_count_api(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'count': 0})
    
    count = notification.objects.filter(user_id=user_id, status='unread').count()
    return JsonResponse({'count': count})


# USER TICKET VIEWS
def user_tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    tickets = support_ticket.objects.filter(user_id=user_id).order_by('-created_at')
    context = {'tickets': tickets}
    return render(request, 'myapp/user_tickets.html', context)


def user_ticket_detail(request, ticket_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    try:
        ticket = support_ticket.objects.get(id=ticket_id, user_id=user_id)
        notifications = notification.objects.filter(ticket_id=ticket_id).order_by('-created_at')
        
        context = {
            'ticket': ticket,
            'notifications': notifications
        }
        return render(request, 'myapp/user_ticket_detail.html', context)
        
    except support_ticket.DoesNotExist:
        messages.error(request, 'Ticket not found')
        return redirect('user_tickets')


def user_create_ticket(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    if request.method == 'POST':
        try:
            user = user_login.objects.get(id=user_id)
            user_details_obj = user_details.objects.get(user_id=user_id)
            
            ticket = support_ticket(
                user_id=user_id,
                user_name=user.uname,
                user_email=user_details_obj.email,
                issue_type=request.POST.get('issue_type'),
                subject=request.POST.get('subject'),
                message=request.POST.get('message'),
                priority=request.POST.get('priority', 'medium'),
                status='open'
            )
            ticket.save()
            
            # Create notification for admin
            notification.objects.create(
                user_id=user_id,
                ticket_id=ticket.id,
                message=f'New support ticket #{ticket.id} created',
                status='unread'
            )
            
            messages.success(request, f'Ticket #{ticket.id} created successfully!')
            return redirect('user_tickets')
            
        except Exception as e:
            messages.error(request, f'Error creating ticket: {str(e)}')
            return render(request, 'myapp/user_create_ticket.html')
    
    return render(request, 'myapp/user_create_ticket.html')


def user_storage_stats(request):
    """AJAX endpoint for storage statistics"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        ufm_l = user_file_map.objects.filter(user_id=user_id)
        sd = storage_details.objects.get(user_id=user_id)
        
        total_bytes = int(sd.total)
        used_bytes = int(sd.used)
        free_bytes = total_bytes - used_bytes
        
        total_gb = round(total_bytes / (1024**3), 2)
        used_gb = round(used_bytes / (1024**3), 2)
        free_gb = round(free_bytes / (1024**3), 2)
        usage_percent = round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0
        
        return JsonResponse({
            'total_files': len(ufm_l),
            'total_gb': total_gb,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'usage_percent': usage_percent
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    if request.method == 'POST':
        try:
            notification_obj = notification.objects.get(id=notification_id)
            notification_obj.status = 'read'
            notification_obj.save()
            return JsonResponse({'success': True})
        except notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=405)


def user_profile_data(request):
    """AJAX endpoint to fetch user profile data"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        user_details_obj = user_details.objects.get(user_id=user_id)
        data = {
            'success': True,
            'full_name': f"{user_details_obj.fname} {user_details_obj.lname}".strip(),
            'email': user_details_obj.email,
            'contact': user_details_obj.contact,
            'location': f"{user_details_obj.addr}, {user_details_obj.pin}".strip(', ')
        }
        return JsonResponse(data)
    except user_details.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User details not found'})


def user_file_search_ajax(request):
    """AJAX endpoint for real-time file search"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'files': []})
    
    try:
        # Search files from user_file_map
        files = user_file_map.objects.filter(
            user_id=user_id, 
            file_name__icontains=query
        ).order_by('-id')[:10]
        
        file_list = []
        for file in files:
            # Get file size from file_index
            try:
                file_index_obj = file_index.objects.get(id=file.file_id)
                file_size = file_index_obj.file_size
            except:
                file_size = 0
                
            file_list.append({
                'id': file.id,
                'name': file.file_name,
                'size': file_size,
                'date': file.dt,
            })
        
        return JsonResponse({'files': file_list})
    except Exception as e:
        return JsonResponse({'error': str(e), 'files': []}, status=500)
# ==================== FILE SHARING FEATURE ====================

def generate_share_link(request, file_id):
    """Generate a share link for another user"""
    if request.method == 'POST':
        try:
            user_file = user_file_map.objects.get(id=file_id, user_id=request.session['user_id'])
            file_obj = file_index.objects.get(id=user_file.file_id)
            
            # Get the user to share with
            shared_with_username = request.POST.get('shared_with_username', '')
            expires_days = int(request.POST.get('expires_days', 7))
            
            # Find the user to share with
            try:
                shared_with_user = user_login.objects.get(uname=shared_with_username, u_type='user')
            except user_login.DoesNotExist:
                messages.error(request, f'User "{shared_with_username}" not found. Please enter a valid username.')
                return redirect('generate_share_link', file_id=file_id)
            
            # Don't allow sharing with self
            if shared_with_user.id == request.session['user_id']:
                messages.error(request, 'You cannot share a file with yourself.')
                return redirect('generate_share_link', file_id=file_id)
            
            # Calculate expiration
            expires_at = None
            if expires_days > 0:
                expires_at = timezone.now() + timezone.timedelta(days=expires_days)
            
            # Generate unique token
            token = str(uuid.uuid4()).replace('-', '')[:32]
            
            # Create share link
            share_link = SharedLink(
                file=file_obj,
                shared_by=user_login.objects.get(id=request.session['user_id']),
                shared_with_user=shared_with_user,
                token=token,
                expires_at=expires_at,
                is_active=True
            )
            share_link.save()
            
            # Create notification for the recipient
            notification.objects.create(
                user_id=shared_with_user.id,
                message=f'{request.session["user_name"]} shared a file "{user_file.file_name}" with you. Click to view.',
                status='unread'
            )
            
            messages.success(request, f'File shared successfully with {shared_with_username}!')
            return redirect('user_file_store_view')
                
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('user_file_store_view')
    
    # GET request - show share form
    try:
        user_file = user_file_map.objects.get(id=file_id, user_id=request.session['user_id'])
        return render(request, 'myapp/create_share_link.html', {'file': user_file})
    except:
        messages.error(request, 'File not found')
        return redirect('user_file_store_view')

def view_shared_file(request, token):
    """View shared file (only for logged-in users)"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to view shared files.')
        return redirect('user_login')
    
    try:
        share_link = SharedLink.objects.get(token=token, is_active=True)
        current_user_id = request.session['user_id']
        
        # Check if this share is meant for the current user
        if share_link.shared_with_user.id != current_user_id:
            messages.error(request, 'You do not have permission to access this file.')
            return redirect('user_home')
        
        # Check if expired
        if share_link.is_expired():
            return render(request, 'myapp/share_expired.html', {'message': 'This share link has expired.'})
        
        # Get file details
        user_file = user_file_map.objects.filter(file_id=share_link.file.id).first()
        
        context = {
            'share_link': share_link,
            'file_name': user_file.file_name if user_file else share_link.file.fname,
            'file_size': share_link.file.file_size,
            'shared_by': share_link.shared_by.uname,
            'token': token
        }
        
        return render(request, 'myapp/view_shared_file.html', context)
        
    except SharedLink.DoesNotExist:
        return render(request, 'myapp/share_expired.html', {'message': 'Invalid share link.'})

def download_shared_file(request, token):
    """Download shared file (only for logged-in users)"""
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login to download shared files.')
        return redirect('user_login')
    
    if request.method == 'POST':
        try:
            share_link = SharedLink.objects.get(token=token, is_active=True)
            current_user_id = request.session['user_id']
            
            # Check permission
            if share_link.shared_with_user.id != current_user_id:
                messages.error(request, 'You do not have permission to download this file.')
                return redirect('user_home')
            
            # Check if expired
            if share_link.is_expired():
                return render(request, 'myapp/share_expired.html', {'message': 'Link expired.'})
            
            # Update access time
            share_link.accessed_at = timezone.now()
            share_link.save()
            
            # Get the file
            user_file = user_file_map.objects.filter(file_id=share_link.file.id).first()
            file_path = os.path.join(BASE_DIR, f'myapp\\static\\myapp\\media\\{share_link.file.fname}')
            
            if not os.path.exists(file_path):
                return render(request, 'myapp/share_expired.html', {'message': 'File not found on server.'})
            
            # Serve the file
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{user_file.file_name}"'
                return response
                
        except SharedLink.DoesNotExist:
            return render(request, 'myapp/share_expired.html', {'message': 'Invalid link.'})
    
    return redirect('view_shared_file', token=token)

def my_shared_links(request):
    """View all files shared by user"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    shared_links = SharedLink.objects.filter(shared_by_id=user_id).order_by('-created_at')
    
    for link in shared_links:
        user_file = user_file_map.objects.filter(file_id=link.file.id).first()
        link.file_name = user_file.file_name if user_file else link.file.fname
        link.is_expired_status = link.is_expired()
    
    return render(request, 'myapp/my_shared_links.html', {
        'shared_links': shared_links,
        'total_shares': shared_links.count()
    })


def revoke_share_link(request, link_id):
    """Revoke a share link"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('user_login')
    
    try:
        share_link = SharedLink.objects.get(id=link_id, shared_by_id=user_id)
        share_link.is_active = False
        share_link.save()
        messages.success(request, 'Share link revoked.')
    except:
        messages.error(request, 'Share link not found.')
    
    return redirect('my_shared_links')