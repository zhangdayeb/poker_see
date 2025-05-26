#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标记管理模块 - 处理摄像头位置标记的业务逻辑
功能:
1. 保存单个摄像头标记数据
2. 批量保存标记数据
3. 验证标记数据格式
4. 标记数据的业务逻辑处理
"""

from typing import Dict, Any, List
from utils import (
    validate_camera_id, validate_mark_position,
    format_success_response, format_error_response,
    log_info, log_success, log_error, log_warning, get_timestamp
)
from config_manager import update_camera_marks, get_camera_by_id

class MarkManager:
    """标记管理器"""
    
    def __init__(self):
        """初始化标记管理器"""
        log_info("标记管理器初始化完成", "MARK")
    
    def save_camera_marks(self, camera_id: str, marks_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存指定摄像头的标记数据
        
        Args:
            camera_id: 摄像头ID
            marks_data: 标记数据，格式: {"marks": {"position": {"x": 0, "y": 0, ...}}}
            
        Returns:
            保存结果
        """
        try:
            # 验证摄像头ID
            if not validate_camera_id(camera_id):
                return format_error_response("摄像头ID格式无效", "INVALID_CAMERA_ID")
            
            # 检查摄像头是否存在
            camera_result = get_camera_by_id(camera_id)
            if camera_result['status'] != 'success':
                return format_error_response(f"摄像头 {camera_id} 不存在", "CAMERA_NOT_FOUND")
            
            # 验证标记数据格式
            if not isinstance(marks_data, dict):
                return format_error_response("标记数据格式无效", "INVALID_MARKS_FORMAT")
            
            marks = marks_data.get('marks', {})
            if not isinstance(marks, dict):
                return format_error_response("标记数据中的marks字段格式无效", "INVALID_MARKS_FIELD")
            
            # 验证和处理每个标记点
            validated_marks = {}
            validation_errors = []
            
            for position_key, position_data in marks.items():
                validation_result = self._validate_and_process_mark(position_key, position_data)
                
                if validation_result['valid']:
                    validated_marks[position_key] = validation_result['data']
                else:
                    validation_errors.append(f"{position_key}: {validation_result['error']}")
            
            if not validated_marks:
                error_msg = "没有有效的标记数据"
                if validation_errors:
                    error_msg += f": {'; '.join(validation_errors)}"
                return format_error_response(error_msg, "NO_VALID_MARKS")
            
            # 调用配置管理器保存数据
            save_result = update_camera_marks(camera_id, validated_marks)
            
            if save_result['status'] == 'success':
                # 记录验证错误（如果有的话）
                if validation_errors:
                    log_warning(f"摄像头 {camera_id} 部分标记数据无效: {'; '.join(validation_errors)}", "MARK")
                
                log_success(f"摄像头 {camera_id} 标记数据保存成功 ({len(validated_marks)} 个有效标记)", "MARK")
                
                return format_success_response(
                    f"摄像头 {camera_id} 标记数据保存成功",
                    data={
                        'camera_id': camera_id,
                        'saved_marks': len(validated_marks),
                        'validation_errors': validation_errors if validation_errors else None
                    }
                )
            else:
                return save_result
                
        except Exception as e:
            log_error(f"保存摄像头 {camera_id} 标记数据失败: {e}", "MARK")
            return format_error_response(f"保存标记数据失败: {str(e)}", "SAVE_MARKS_ERROR")
    
    def batch_save_marks(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量保存标记数据
        
        Args:
            batch_data: 批量数据，格式: {"cameras": [{"camera_id": "001", "marks": {...}}, ...]}
            
        Returns:
            批量保存结果
        """
        try:
            # 验证批量数据格式
            if not isinstance(batch_data, dict):
                return format_error_response("批量数据格式无效", "INVALID_BATCH_FORMAT")
            
            cameras_data = batch_data.get('cameras', [])
            if not isinstance(cameras_data, list):
                return format_error_response("cameras字段必须是列表格式", "INVALID_CAMERAS_FIELD")
            
            if not cameras_data:
                return format_error_response("没有摄像头数据需要处理", "NO_CAMERA_DATA")
            
            # 批量处理结果
            results = []
            success_count = 0
            error_count = 0
            
            for i, camera_data in enumerate(cameras_data):
                if not isinstance(camera_data, dict):
                    results.append({
                        'index': i,
                        'camera_id': 'unknown',
                        'status': 'error',
                        'message': '摄像头数据格式无效'
                    })
                    error_count += 1
                    continue
                
                camera_id = camera_data.get('camera_id')
                marks = camera_data.get('marks', {})
                
                # 处理单个摄像头的标记数据
                save_result = self.save_camera_marks(camera_id, {'marks': marks})
                
                result_summary = {
                    'index': i,
                    'camera_id': camera_id,
                    'status': save_result['status'],
                    'message': save_result['message']
                }
                
                if save_result['status'] == 'success':
                    success_count += 1
                    result_summary['saved_marks'] = save_result['data'].get('saved_marks', 0)
                else:
                    error_count += 1
                    result_summary['error_code'] = save_result.get('error_code')
                
                results.append(result_summary)
            
            # 汇总结果
            total_processed = len(cameras_data)
            overall_status = 'success' if error_count == 0 else ('partial' if success_count > 0 else 'error')
            
            log_info(f"批量保存完成: {success_count}/{total_processed} 成功", "MARK")
            
            return format_success_response(
                f"批量保存完成: {success_count}/{total_processed} 成功",
                data={
                    'overall_status': overall_status,
                    'total_processed': total_processed,
                    'success_count': success_count,
                    'error_count': error_count,
                    'results': results
                }
            )
            
        except Exception as e:
            log_error(f"批量保存标记数据失败: {e}", "MARK")
            return format_error_response(f"批量保存失败: {str(e)}", "BATCH_SAVE_ERROR")
    
    def validate_marks_data(self, marks_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证标记数据格式（不保存，仅验证）
        
        Args:
            marks_data: 标记数据
            
        Returns:
            验证结果
        """
        try:
            if not isinstance(marks_data, dict):
                return format_error_response("标记数据必须是字典格式", "INVALID_FORMAT")
            
            marks = marks_data.get('marks', {})
            if not isinstance(marks, dict):
                return format_error_response("marks字段必须是字典格式", "INVALID_MARKS_FIELD")
            
            validation_results = {}
            valid_count = 0
            error_count = 0
            
            for position_key, position_data in marks.items():
                result = self._validate_and_process_mark(position_key, position_data)
                validation_results[position_key] = {
                    'valid': result['valid'],
                    'message': result['error'] if not result['valid'] else 'valid',
                    'processed_data': result['data'] if result['valid'] else None
                }
                
                if result['valid']:
                    valid_count += 1
                else:
                    error_count += 1
            
            overall_valid = error_count == 0
            
            return format_success_response(
                f"验证完成: {valid_count}/{len(marks)} 有效",
                data={
                    'overall_valid': overall_valid,
                    'total_marks': len(marks),
                    'valid_count': valid_count,
                    'error_count': error_count,
                    'validation_results': validation_results
                }
            )
            
        except Exception as e:
            log_error(f"验证标记数据失败: {e}", "MARK")
            return format_error_response(f"验证失败: {str(e)}", "VALIDATION_ERROR")
    
    def _validate_and_process_mark(self, position_key: str, position_data: Any) -> Dict[str, Any]:
        """
        验证和处理单个标记点数据
        
        Args:
            position_key: 位置键
            position_data: 位置数据
            
        Returns:
            验证和处理结果
        """
        try:
            # 验证位置键
            valid_positions = ['zhuang_1', 'zhuang_2', 'zhuang_3', 'xian_1', 'xian_2', 'xian_3']
            if position_key not in valid_positions:
                return {
                    'valid': False,
                    'error': f'无效的位置键: {position_key}',
                    'data': None
                }
            
            # 验证位置数据格式
            if not isinstance(position_data, dict):
                return {
                    'valid': False,
                    'error': '位置数据必须是字典格式',
                    'data': None
                }
            
            # 验证必需字段
            required_fields = ['x', 'y']
            for field in required_fields:
                if field not in position_data:
                    return {
                        'valid': False,
                        'error': f'缺少必需字段: {field}',
                        'data': None
                    }
                
                # 验证坐标值
                try:
                    value = float(position_data[field])
                    if value < 0:
                        return {
                            'valid': False,
                            'error': f'坐标值 {field} 不能为负数',
                            'data': None
                        }
                except (ValueError, TypeError):
                    return {
                        'valid': False,
                        'error': f'坐标值 {field} 必须是数字',
                        'data': None
                    }
            
            # 处理数据，添加默认值和时间戳
            processed_data = {
                'x': float(position_data['x']),
                'y': float(position_data['y']),
                'width': float(position_data.get('width', 50)),
                'height': float(position_data.get('height', 70)),
                'marked': True,
                'updated_at': get_timestamp(),
                'validation_passed': True
            }
            
            # 验证可选字段
            optional_fields = ['width', 'height', 'rotation', 'description']
            for field in optional_fields:
                if field in position_data:
                    if field in ['width', 'height', 'rotation']:
                        try:
                            processed_data[field] = float(position_data[field])
                        except (ValueError, TypeError):
                            log_warning(f"忽略无效的 {field} 值: {position_data[field]}", "MARK")
                    else:
                        processed_data[field] = str(position_data[field])
            
            return {
                'valid': True,
                'error': None,
                'data': processed_data
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'处理标记数据时出错: {str(e)}',
                'data': None
            }
    
    def get_mark_statistics(self, camera_id: str = None) -> Dict[str, Any]:
        """
        获取标记统计信息
        
        Args:
            camera_id: 摄像头ID，如果为None则统计所有摄像头
            
        Returns:
            标记统计信息
        """
        try:
            from config_manager import get_all_cameras, get_camera_by_id
            
            if camera_id:
                # 获取单个摄像头的统计信息
                camera_result = get_camera_by_id(camera_id)
                if camera_result['status'] != 'success':
                    return camera_result
                
                cameras = [camera_result['data']['camera']]
            else:
                # 获取所有摄像头的统计信息
                all_cameras_result = get_all_cameras()
                if all_cameras_result['status'] != 'success':
                    return all_cameras_result
                
                cameras = all_cameras_result['data']['cameras']
            
            # 计算统计信息
            total_cameras = len(cameras)
            total_positions = 0
            marked_positions = 0
            camera_stats = []
            
            for camera in cameras:
                cam_id = camera.get('id')
                mark_positions = camera.get('mark_positions', {})
                
                cam_total = len(mark_positions)
                cam_marked = sum(1 for pos_data in mark_positions.values() 
                               if pos_data.get('marked', False))
                
                total_positions += cam_total
                marked_positions += cam_marked
                
                camera_stats.append({
                    'camera_id': cam_id,
                    'camera_name': camera.get('name', ''),
                    'total_positions': cam_total,
                    'marked_positions': cam_marked,
                    'completion_rate': round((cam_marked / cam_total * 100) if cam_total > 0 else 0, 1),
                    'last_updated': camera.get('updated_at', '')
                })
            
            overall_completion = round((marked_positions / total_positions * 100) if total_positions > 0 else 0, 1)
            
            return format_success_response(
                "获取标记统计成功",
                data={
                    'total_cameras': total_cameras,
                    'total_positions': total_positions,
                    'marked_positions': marked_positions,
                    'overall_completion_rate': overall_completion,
                    'camera_statistics': camera_stats
                }
            )
            
        except Exception as e:
            log_error(f"获取标记统计失败: {e}", "MARK")
            return format_error_response(f"获取统计信息失败: {str(e)}", "STATS_ERROR")
    
    def export_marks_data(self, camera_id: str = None, format_type: str = 'json') -> Dict[str, Any]:
        """
        导出标记数据
        
        Args:
            camera_id: 摄像头ID，如果为None则导出所有摄像头
            format_type: 导出格式 ('json', 'csv')
            
        Returns:
            导出结果
        """
        try:
            from config_manager import get_all_cameras, get_camera_by_id
            
            if camera_id:
                camera_result = get_camera_by_id(camera_id)
                if camera_result['status'] != 'success':
                    return camera_result
                cameras = [camera_result['data']['camera']]
            else:
                all_cameras_result = get_all_cameras()
                if all_cameras_result['status'] != 'success':
                    return all_cameras_result
                cameras = all_cameras_result['data']['cameras']
            
            if format_type.lower() == 'json':
                export_data = {
                    'export_time': get_timestamp(),
                    'total_cameras': len(cameras),
                    'cameras': []
                }
                
                for camera in cameras:
                    camera_export = {
                        'camera_id': camera.get('id'),
                        'camera_name': camera.get('name'),
                        'marks': camera.get('mark_positions', {})
                    }
                    export_data['cameras'].append(camera_export)
                
                return format_success_response(
                    "标记数据导出成功",
                    data=export_data
                )
            
            elif format_type.lower() == 'csv':
                # CSV格式导出（简化版）
                csv_data = []
                csv_data.append(['camera_id', 'camera_name', 'position', 'x', 'y', 'width', 'height', 'marked', 'updated_at'])
                
                for camera in cameras:
                    cam_id = camera.get('id', '')
                    cam_name = camera.get('name', '')
                    mark_positions = camera.get('mark_positions', {})
                    
                    for position, pos_data in mark_positions.items():
                        csv_data.append([
                            cam_id,
                            cam_name,
                            position,
                            pos_data.get('x', 0),
                            pos_data.get('y', 0),
                            pos_data.get('width', 0),
                            pos_data.get('height', 0),
                            pos_data.get('marked', False),
                            pos_data.get('updated_at', '')
                        ])
                
                return format_success_response(
                    "标记数据CSV导出成功",
                    data={'csv_data': csv_data}
                )
            
            else:
                return format_error_response(f"不支持的导出格式: {format_type}", "UNSUPPORTED_FORMAT")
                
        except Exception as e:
            log_error(f"导出标记数据失败: {e}", "MARK")
            return format_error_response(f"导出失败: {str(e)}", "EXPORT_ERROR")

# 创建全局实例
mark_manager = MarkManager()

# 导出主要函数
def save_camera_marks(camera_id: str, marks_data: Dict[str, Any]) -> Dict[str, Any]:
    """保存摄像头标记数据"""
    return mark_manager.save_camera_marks(camera_id, marks_data)

def batch_save_marks(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """批量保存标记数据"""
    return mark_manager.batch_save_marks(batch_data)

def validate_marks_data(marks_data: Dict[str, Any]) -> Dict[str, Any]:
    """验证标记数据格式"""
    return mark_manager.validate_marks_data(marks_data)

def get_mark_statistics(camera_id: str = None) -> Dict[str, Any]:
    """获取标记统计信息"""
    return mark_manager.get_mark_statistics(camera_id)

def export_marks_data(camera_id: str = None, format_type: str = 'json') -> Dict[str, Any]:
    """导出标记数据"""
    return mark_manager.export_marks_data(camera_id, format_type)

if __name__ == "__main__":
    # 测试标记管理器
    print("🧪 测试标记管理器")
    
    # 测试标记数据
    test_marks_data = {
        "marks": {
            "zhuang_1": {"x": 100, "y": 150, "width": 60, "height": 80},
            "xian_1": {"x": 200, "y": 250, "width": 55, "height": 75},
            "invalid_position": {"x": 300, "y": 350}  # 无效位置
        }
    }
    
    # 测试验证标记数据
    validation_result = validate_marks_data(test_marks_data)
    print(f"验证结果: {validation_result}")
    
    # 测试保存标记数据
    save_result = save_camera_marks("001", test_marks_data)
    print(f"保存结果: {save_result}")
    
    # 测试批量保存
    batch_data = {
        "cameras": [
            {"camera_id": "001", "marks": {"zhuang_2": {"x": 120, "y": 160}}},
            {"camera_id": "002", "marks": {"xian_2": {"x": 220, "y": 260}}}  # 可能不存在的摄像头
        ]
    }
    batch_result = batch_save_marks(batch_data)
    print(f"批量保存结果: {batch_result}")
    
    # 测试统计信息
    stats = get_mark_statistics()
    print(f"统计信息: {stats}")
    
    print("✅ 标记管理器测试完成")