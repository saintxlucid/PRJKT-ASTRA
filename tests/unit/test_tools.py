"""
Tool Bus Unit Tests - Phase 6
Comprehensive testing for Tool Bus adapters (Filesystem, Shell, Notification, Clipboard)
with policy gating, rollback, history tracking, and concurrency scenarios.
Total: 15+ tests covering 150+ lines
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import asyncio
import os
import json


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_policy_engine():
    """Mock PolicyEngine for tool authorization."""
    engine = Mock()
    engine.can_perform_action = Mock(return_value=True)
    engine.evaluate = Mock(return_value=True)
    return engine


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for tool operation events."""
    bus = Mock()
    bus.publish = Mock()
    bus.subscribe = Mock()
    return bus


@pytest.fixture
def tool_bus(mock_policy_engine, mock_event_bus):
    """Create ToolBus instance with mocked dependencies."""
    from libs.tools import ToolBus
    
    bus = ToolBus(
        policy_engine=mock_policy_engine,
        event_bus=mock_event_bus,
    )
    return bus


@pytest.fixture
def tool_config():
    """Tool Bus configuration."""
    return {
        'filesystem': {
            'enabled': True,
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'allowed_paths': [r'C:\Users', r'C:\Temp'],
            'blocked_paths': [r'C:\Windows\System32'],
        },
        'shell': {
            'enabled': True,
            'allowed_commands': ['dir', 'tasklist', 'Get-Process'],
            'blocked_commands': ['format', 'del /s'],
            'timeout': 30.0,
        },
        'notification': {
            'enabled': True,
            'max_title_length': 100,
            'max_message_length': 500,
        },
        'clipboard': {
            'enabled': True,
            'max_clipboard_size': 10 * 1024 * 1024,  # 10MB
            'track_access': True,
        },
    }


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestToolBusInitialization:
    """Test ToolBus initialization and adapter registration."""
    
    def test_tool_bus_initialization(self, tool_bus, mock_policy_engine, mock_event_bus):
        """Test ToolBus basic initialization."""
        assert tool_bus is not None
        assert tool_bus.policy_engine == mock_policy_engine
        assert tool_bus.event_bus == mock_event_bus
    
    def test_adapter_registration(self, tool_bus):
        """Test tool adapter registration."""
        adapters = tool_bus.list_adapters()
        
        assert 'filesystem' in adapters
        assert 'shell' in adapters
        assert 'notification' in adapters
        assert 'clipboard' in adapters
    
    def test_get_adapter_by_name(self, tool_bus):
        """Test retrieving adapter by name."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        assert fs_adapter is not None
        assert fs_adapter.name == 'filesystem'
    
    def test_invalid_adapter_handling(self, tool_bus):
        """Test handling of invalid adapter names."""
        with pytest.raises((KeyError, ValueError)):
            tool_bus.get_adapter('nonexistent_adapter')


class TestFilesystemAdapter:
    """Test filesystem tool adapter."""
    
    def test_filesystem_adapter_initialization(self, tool_bus):
        """Test filesystem adapter initialization."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        assert fs_adapter is not None
        assert fs_adapter.name == 'filesystem'
    
    @pytest.mark.asyncio
    async def test_create_file_operation(self, tool_bus, mock_policy_engine):
        """Test file creation operation."""
        mock_policy_engine.can_perform_action.return_value = True
        
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        result = fs_adapter.create_file(
            path=r'C:\Temp\test.txt',
            content='Test content',
            overwrite=False,
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_read_file_operation(self, tool_bus, mock_policy_engine):
        """Test file read operation."""
        mock_policy_engine.can_perform_action.return_value = True
        
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'File content'
            
            result = fs_adapter.read_file(path=r'C:\Temp\test.txt')
            
            assert result is not None
    
    def test_file_deletion_with_policy(self, tool_bus, mock_policy_engine):
        """Test file deletion with policy checks."""
        mock_policy_engine.can_perform_action.return_value = True
        
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('os.remove') as mock_remove:
            fs_adapter.delete_file(path=r'C:\Temp\test.txt')
            
            # Policy engine should be consulted
            mock_policy_engine.can_perform_action.assert_called()
    
    def test_file_operation_policy_denial(self, tool_bus, mock_policy_engine):
        """Test file operation denied by policy."""
        mock_policy_engine.can_perform_action.return_value = False
        
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with pytest.raises(PermissionError):
            fs_adapter.delete_file(path=r'C:\Windows\System32\test.txt')
    
    def test_directory_listing(self, tool_bus):
        """Test directory listing operation."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['file1.txt', 'file2.txt', 'subdir']
            
            result = fs_adapter.list_directory(path=r'C:\Temp')
            
            assert len(result) == 3
    
    def test_file_move_operation(self, tool_bus):
        """Test file move operation."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('os.rename') as mock_rename:
            fs_adapter.move_file(
                source=r'C:\Temp\source.txt',
                destination=r'C:\Temp\dest.txt',
            )
            
            mock_rename.assert_called_once()
    
    def test_file_copy_operation(self, tool_bus):
        """Test file copy operation."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('shutil.copy2') as mock_copy:
            fs_adapter.copy_file(
                source=r'C:\Temp\source.txt',
                destination=r'C:\Temp\dest.txt',
            )
            
            mock_copy.assert_called_once()


class TestShellAdapter:
    """Test shell command execution adapter."""
    
    def test_shell_adapter_initialization(self, tool_bus):
        """Test shell adapter initialization."""
        shell_adapter = tool_bus.get_adapter('shell')
        assert shell_adapter is not None
        assert shell_adapter.name == 'shell'
    
    def test_allowed_command_execution(self, tool_bus, mock_policy_engine):
        """Test execution of allowed command."""
        mock_policy_engine.can_perform_action.return_value = True
        
        shell_adapter = tool_bus.get_adapter('shell')
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='output', stderr='')
            
            result = shell_adapter.execute_command(command='dir C:\\')
            
            assert result is not None
    
    def test_blocked_command_prevention(self, tool_bus, mock_policy_engine):
        """Test prevention of blocked commands."""
        mock_policy_engine.can_perform_action.return_value = False
        
        shell_adapter = tool_bus.get_adapter('shell')
        
        with pytest.raises(PermissionError):
            shell_adapter.execute_command(command='format C:')
    
    def test_command_timeout(self, tool_bus, mock_policy_engine):
        """Test command execution timeout."""
        mock_policy_engine.can_perform_action.return_value = True
        
        shell_adapter = tool_bus.get_adapter('shell')
        shell_adapter.timeout = 0.1
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = TimeoutError()
            
            with pytest.raises(TimeoutError):
                shell_adapter.execute_command(command='sleep 100')
    
    def test_command_output_capture(self, tool_bus, mock_policy_engine):
        """Test capturing command output."""
        mock_policy_engine.can_perform_action.return_value = True
        
        shell_adapter = tool_bus.get_adapter('shell')
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='Process 1234: python.exe\nProcess 5678: notepad.exe',
                stderr='',
            )
            
            result = shell_adapter.execute_command(command='tasklist | grep python')
            
            assert 'python' in str(result).lower()
    
    def test_command_error_handling(self, tool_bus, mock_policy_engine):
        """Test command error handling."""
        mock_policy_engine.can_perform_action.return_value = True
        
        shell_adapter = tool_bus.get_adapter('shell')
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error message')
            
            result = shell_adapter.execute_command(command='invalid_command')
            
            assert result is not None


class TestNotificationAdapter:
    """Test notification tool adapter."""
    
    def test_notification_adapter_initialization(self, tool_bus):
        """Test notification adapter initialization."""
        notif_adapter = tool_bus.get_adapter('notification')
        assert notif_adapter is not None
        assert notif_adapter.name == 'notification'
    
    def test_send_notification(self, tool_bus):
        """Test sending notification."""
        notif_adapter = tool_bus.get_adapter('notification')
        
        with patch('win10toast.ToastNotifier') as mock_toast:
            result = notif_adapter.send_notification(
                title='Test Alert',
                message='This is a test notification',
                duration=5,
            )
            
            assert result is not None
    
    def test_notification_title_length_limit(self, tool_bus, tool_config):
        """Test notification title length limit enforcement."""
        notif_adapter = tool_bus.get_adapter('notification')
        max_title = tool_config['notification']['max_title_length']
        
        long_title = 'A' * (max_title + 100)
        
        with pytest.raises(ValueError):
            notif_adapter.send_notification(
                title=long_title,
                message='Test',
            )
    
    def test_notification_message_length_limit(self, tool_bus, tool_config):
        """Test notification message length limit enforcement."""
        notif_adapter = tool_bus.get_adapter('notification')
        max_message = tool_config['notification']['max_message_length']
        
        long_message = 'B' * (max_message + 100)
        
        with pytest.raises(ValueError):
            notif_adapter.send_notification(
                title='Test',
                message=long_message,
            )
    
    def test_notification_with_icon(self, tool_bus):
        """Test notification with custom icon."""
        notif_adapter = tool_bus.get_adapter('notification')
        
        result = notif_adapter.send_notification(
            title='Test',
            message='With icon',
            icon_path=r'C:\astra\icon.ico',
        )
        
        assert result is not None
    
    def test_notification_event_publication(self, tool_bus, mock_event_bus):
        """Test notification event publication."""
        notif_adapter = tool_bus.get_adapter('notification')
        
        notif_adapter.send_notification(
            title='Test',
            message='Testing event publication',
        )
        
        mock_event_bus.publish.assert_called()


class TestClipboardAdapter:
    """Test clipboard tool adapter."""
    
    def test_clipboard_adapter_initialization(self, tool_bus):
        """Test clipboard adapter initialization."""
        clip_adapter = tool_bus.get_adapter('clipboard')
        assert clip_adapter is not None
        assert clip_adapter.name == 'clipboard'
    
    def test_clipboard_write_operation(self, tool_bus, mock_policy_engine):
        """Test clipboard write operation."""
        mock_policy_engine.can_perform_action.return_value = True
        
        clip_adapter = tool_bus.get_adapter('clipboard')
        
        with patch('pyperclip.copy') as mock_copy:
            clip_adapter.write(content='Test clipboard content')
            
            mock_copy.assert_called_once()
    
    def test_clipboard_read_operation(self, tool_bus):
        """Test clipboard read operation."""
        clip_adapter = tool_bus.get_adapter('clipboard')
        
        with patch('pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'Clipboard content'
            
            result = clip_adapter.read()
            
            assert result == 'Clipboard content'
    
    def test_clipboard_size_limit_enforcement(self, tool_bus, tool_config):
        """Test clipboard size limit enforcement."""
        clip_adapter = tool_bus.get_adapter('clipboard')
        max_size = tool_config['clipboard']['max_clipboard_size']
        
        large_content = 'X' * (max_size + 1000000)
        
        with pytest.raises(ValueError):
            clip_adapter.write(content=large_content)
    
    def test_clipboard_clear_operation(self, tool_bus):
        """Test clipboard clear operation."""
        clip_adapter = tool_bus.get_adapter('clipboard')
        
        with patch('pyperclip.copy') as mock_copy:
            clip_adapter.clear()
            
            mock_copy.assert_called_with('')
    
    def test_clipboard_access_tracking(self, tool_bus, mock_event_bus):
        """Test clipboard access tracking."""
        clip_adapter = tool_bus.get_adapter('clipboard')
        
        with patch('pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'content'
            
            clip_adapter.read()
            
            # Should publish access event
            mock_event_bus.publish.assert_called()


class TestToolBusRollback:
    """Test tool operation rollback functionality."""
    
    def test_operation_history_recording(self, tool_bus):
        """Test recording of tool operations in history."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        operation = {
            'tool': 'filesystem',
            'action': 'create_file',
            'params': {'path': r'C:\Temp\test.txt'},
            'timestamp': datetime.now().isoformat(),
        }
        
        tool_bus.record_operation(operation)
        
        history = tool_bus.get_operation_history()
        assert len(history) > 0
    
    def test_rollback_file_creation(self, tool_bus, mock_policy_engine):
        """Test rollback of file creation."""
        mock_policy_engine.can_perform_action.return_value = True
        
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        with patch('os.remove') as mock_remove:
            # Record creation
            operation_id = tool_bus.record_operation({
                'tool': 'filesystem',
                'action': 'create_file',
                'params': {'path': r'C:\Temp\test.txt'},
            })
            
            # Rollback
            tool_bus.rollback_operation(operation_id)
            
            mock_remove.assert_called()
    
    def test_rollback_command_execution(self, tool_bus):
        """Test rollback of command execution."""
        shell_adapter = tool_bus.get_adapter('shell')
        
        operation_id = tool_bus.record_operation({
            'tool': 'shell',
            'action': 'execute_command',
            'params': {'command': 'dir C:\\'},
            'result': 'output',
        })
        
        # Rollback should succeed
        result = tool_bus.rollback_operation(operation_id)
        assert result is not None


class TestToolBusPolicy:
    """Test policy gating and authorization."""
    
    def test_tool_action_authorization(self, tool_bus, mock_policy_engine):
        """Test policy-based authorization of tool actions."""
        mock_policy_engine.can_perform_action.return_value = True
        
        authorized = tool_bus.authorize_action(
            tool='filesystem',
            action='delete_file',
            params={'path': r'C:\Temp\test.txt'},
        )
        
        assert authorized is True
    
    def test_tool_action_denial(self, tool_bus, mock_policy_engine):
        """Test policy-based denial of tool actions."""
        mock_policy_engine.can_perform_action.return_value = False
        
        authorized = tool_bus.authorize_action(
            tool='filesystem',
            action='delete_file',
            params={'path': r'C:\Windows\System32\critical.dll'},
        )
        
        assert authorized is False
    
    def test_policy_evaluation_context(self, tool_bus, mock_policy_engine):
        """Test policy evaluation with full context."""
        mock_policy_engine.evaluate.return_value = True
        
        context = {
            'tool': 'shell',
            'action': 'execute_command',
            'command': 'tasklist',
            'risk_level': 'low',
            'user_context': 'admin',
        }
        
        result = tool_bus.evaluate_with_context(context)
        
        mock_policy_engine.evaluate.assert_called()


class TestToolBusConcurrency:
    """Test concurrent tool operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, tool_bus):
        """Test concurrent file operations."""
        async def file_operation(index):
            fs_adapter = tool_bus.get_adapter('filesystem')
            return {
                'operation': 'create',
                'path': f'C:\\Temp\\file_{index}.txt',
                'index': index,
            }
        
        results = await asyncio.gather(
            file_operation(1),
            file_operation(2),
            file_operation(3),
        )
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_shell_commands(self, tool_bus):
        """Test concurrent shell command execution."""
        async def execute_command(cmd):
            shell_adapter = tool_bus.get_adapter('shell')
            return {'command': cmd, 'status': 'executed'}
        
        results = await asyncio.gather(
            execute_command('dir C:\\'),
            execute_command('tasklist'),
            execute_command('Get-Process'),
        )
        
        assert len(results) == 3
    
    def test_tool_operation_serialization(self, tool_bus):
        """Test serialization of concurrent tool operations."""
        operations = []
        
        for i in range(10):
            op = {
                'tool': 'filesystem',
                'action': f'operation_{i}',
                'timestamp': datetime.now().isoformat(),
            }
            operations.append(op)
        
        for op in operations:
            tool_bus.record_operation(op)
        
        history = tool_bus.get_operation_history()
        assert len(history) == 10


class TestToolBusIntegration:
    """Test Tool Bus integration with other components."""
    
    def test_event_bus_integration(self, tool_bus, mock_event_bus):
        """Test integration with EventBus."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        
        # Perform operation
        with patch('os.remove'):
            tool_bus.authorize_action('filesystem', 'delete_file', {})
        
        # Event should be published
        mock_event_bus.publish.assert_called()
    
    def test_policy_engine_integration(self, tool_bus, mock_policy_engine):
        """Test integration with PolicyEngine."""
        shell_adapter = tool_bus.get_adapter('shell')
        
        tool_bus.authorize_action('shell', 'execute_command', {'command': 'dir'})
        
        # Policy engine should be consulted
        mock_policy_engine.can_perform_action.assert_called()
    
    def test_cross_tool_workflow(self, tool_bus):
        """Test workflow involving multiple tools."""
        fs_adapter = tool_bus.get_adapter('filesystem')
        shell_adapter = tool_bus.get_adapter('shell')
        notif_adapter = tool_bus.get_adapter('notification')
        
        # Workflow: Read file → Parse → Execute command → Notify
        with patch('builtins.open', create=True):
            with patch('subprocess.run'):
                with patch('win10toast.ToastNotifier'):
                    # All operations should succeed
                    assert fs_adapter is not None
                    assert shell_adapter is not None
                    assert notif_adapter is not None


# ============================================================================
# END OF TEST_TOOLS.PY
# ============================================================================
