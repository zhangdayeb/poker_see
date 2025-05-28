#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像预处理器 - 对识别前的图像进行预处理
功能:
1. 图像缩放和裁剪
2. 图像增强（亮度、对比度、饱和度）
3. 噪声去除和滤波
4. 透视矫正
5. 角度检测和旋转
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np

# 添加项目根目录到 Python 路径
def setup_project_paths():
    """设置项目路径，确保可以正确导入模块"""
    current_file = Path(__file__).resolve()
    
    # 找到项目根目录（包含 main.py 的目录）
    project_root = current_file
    while project_root.parent != project_root:
        if (project_root / "main.py").exists():
            break
        project_root = project_root.parent
    
    # 将项目根目录添加到 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root

PROJECT_ROOT = setup_project_paths()

from src.core.utils import log_info, log_success, log_error, log_warning

class ImagePreprocessor:
    """图像预处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化图像预处理器"""
        self.config = config or {}
        self.cv2 = None
        self.pil = None
        self.cv2_available = False
        self.pil_available = False
        
        self._initialize_libraries()
        
        log_info("图像预处理器初始化完成", "PREPROCESSOR")
    
    def _initialize_libraries(self):
        """初始化依赖库"""
        try:
            # 初始化OpenCV
            try:
                import cv2
                self.cv2 = cv2
                self.cv2_available = True
                log_success("OpenCV库加载成功", "PREPROCESSOR")
            except ImportError:
                log_warning("OpenCV库不可用", "PREPROCESSOR")
            
            # 初始化PIL
            try:
                from PIL import Image, ImageEnhance, ImageFilter
                self.pil = Image
                self.pil_enhance = ImageEnhance
                self.pil_filter = ImageFilter
                self.pil_available = True
                log_success("PIL库加载成功", "PREPROCESSOR")
            except ImportError:
                log_warning("PIL库不可用", "PREPROCESSOR")
            
            if not self.cv2_available and not self.pil_available:
                log_error("没有可用的图像处理库", "PREPROCESSOR")
                
        except Exception as e:
            log_error(f"图像处理库初始化失败: {e}", "PREPROCESSOR")
    
    def preprocess_image(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        预处理图像
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径（可选）
            
        Returns:
            预处理结果
        """
        try:
            if not Path(image_path).exists():
                return {
                    'success': False,
                    'error': f'图像文件不存在: {image_path}'
                }
            
            # 获取预处理配置
            pipeline = self.config.get('pipeline', ['resize', 'enhance', 'noise_reduction'])
            
            result = {
                'success': True,
                'original_path': image_path,
                'processed_path': output_path,
                'pipeline_steps': [],
                'processing_info': {}
            }
            
            # 读取图像
            if self.cv2_available:
                image = self.cv2.imread(image_path)
                if image is None:
                    return {
                        'success': False,
                        'error': '无法读取图像文件'
                    }
                current_image = image.copy()
                using_opencv = True
            elif self.pil_available:
                image = self.pil.open(image_path)
                current_image = image.copy()
                using_opencv = False
            else:
                return {
                    'success': False,
                    'error': '没有可用的图像处理库'
                }
            
            # 记录原始图像信息
            if using_opencv:
                original_height, original_width = image.shape[:2]
            else:
                original_width, original_height = image.size
            
            result['processing_info']['original_size'] = (original_width, original_height)
            
            # 执行预处理管道
            for step in pipeline:
                try:
                    if step == 'resize' and self._is_step_enabled('resize'):
                        current_image, step_info = self._resize_image(current_image, using_opencv)
                        result['pipeline_steps'].append('resize')
                        result['processing_info']['resize'] = step_info
                    
                    elif step == 'enhance' and self._is_step_enabled('enhance'):
                        current_image, step_info = self._enhance_image(current_image, using_opencv)
                        result['pipeline_steps'].append('enhance')
                        result['processing_info']['enhance'] = step_info
                    
                    elif step == 'noise_reduction' and self._is_step_enabled('noise_reduction'):
                        current_image, step_info = self._reduce_noise(current_image, using_opencv)
                        result['pipeline_steps'].append('noise_reduction')
                        result['processing_info']['noise_reduction'] = step_info
                    
                    elif step == 'perspective_correction' and self._is_step_enabled('perspective_correction'):
                        current_image, step_info = self._correct_perspective(current_image, using_opencv)
                        result['pipeline_steps'].append('perspective_correction')
                        result['processing_info']['perspective_correction'] = step_info
                        
                except Exception as e:
                    log_warning(f"预处理步骤失败 {step}: {e}", "PREPROCESSOR")
                    result['processing_info'][f'{step}_error'] = str(e)
            
            # 保存处理后的图像
            if output_path:
                success = self._save_image(current_image, output_path, using_opencv)
                if success:
                    result['processed_path'] = output_path
                    log_success(f"预处理图像已保存: {output_path}", "PREPROCESSOR")
                else:
                    result['processed_path'] = None
                    log_error(f"保存预处理图像失败: {output_path}", "PREPROCESSOR")
            
            # 记录最终图像信息
            if using_opencv:
                final_height, final_width = current_image.shape[:2]
            else:
                final_width, final_height = current_image.size
            
            result['processing_info']['final_size'] = (final_width, final_height)
            result['processing_info']['size_changed'] = (original_width, original_height) != (final_width, final_height)
            
            return result
            
        except Exception as e:
            log_error(f"图像预处理失败: {e}", "PREPROCESSOR")
            return {
                'success': False,
                'error': f'图像预处理异常: {str(e)}'
            }
    
    def _is_step_enabled(self, step_name: str) -> bool:
        """检查预处理步骤是否启用"""
        step_config = self.config.get(step_name, {})
        return step_config.get('enabled', True)
    
    def _resize_image(self, image: Union[np.ndarray, Any], using_opencv: bool) -> Tuple[Union[np.ndarray, Any], Dict[str, Any]]:
        """调整图像大小"""
        try:
            config = self.config.get('resize', {})
            target_width = config.get('target_width', 640)
            target_height = config.get('target_height', 480)
            keep_aspect_ratio = config.get('keep_aspect_ratio', True)
            
            if using_opencv:
                original_height, original_width = image.shape[:2]
                
                if keep_aspect_ratio:
                    # 保持宽高比
                    scale = min(target_width / original_width, target_height / original_height)
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                else:
                    new_width = target_width
                    new_height = target_height
                
                interpolation_name = config.get('interpolation', 'INTER_LINEAR')
                interpolation = getattr(self.cv2, interpolation_name, self.cv2.INTER_LINEAR)
                
                resized_image = self.cv2.resize(image, (new_width, new_height), interpolation=interpolation)
                
                return resized_image, {
                    'original_size': (original_width, original_height),
                    'new_size': (new_width, new_height),
                    'scale_factor': scale if keep_aspect_ratio else (new_width/original_width, new_height/original_height)
                }
                
            else:  # PIL
                original_width, original_height = image.size
                
                if keep_aspect_ratio:
                    scale = min(target_width / original_width, target_height / original_height)
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                else:
                    new_width = target_width
                    new_height = target_height
                
                resized_image = image.resize((new_width, new_height), self.pil.LANCZOS)
                
                return resized_image, {
                    'original_size': (original_width, original_height),
                    'new_size': (new_width, new_height),
                    'scale_factor': scale if keep_aspect_ratio else (new_width/original_width, new_height/original_height)
                }
                
        except Exception as e:
            log_error(f"图像缩放失败: {e}", "PREPROCESSOR")
            return image, {'error': str(e)}
    
    def _enhance_image(self, image: Union[np.ndarray, Any], using_opencv: bool) -> Tuple[Union[np.ndarray, Any], Dict[str, Any]]:
        """图像增强"""
        try:
            config = self.config.get('enhance', {})
            brightness_factor = config.get('brightness_factor', 1.1)
            contrast_factor = config.get('contrast_factor', 1.2)
            saturation_factor = config.get('saturation_factor', 1.0)
            sharpness_factor = config.get('sharpness_factor', 1.1)
            auto_adjust = config.get('auto_adjust', True)
            
            enhanced_image = image
            adjustments = {}
            
            if using_opencv:
                # 使用OpenCV进行增强
                if brightness_factor != 1.0 or contrast_factor != 1.0:
                    # 亮度和对比度调整
                    enhanced_image = self.cv2.convertScaleAbs(enhanced_image, 
                                                             alpha=contrast_factor, 
                                                             beta=(brightness_factor - 1.0) * 30)
                    adjustments['brightness'] = brightness_factor
                    adjustments['contrast'] = contrast_factor
                
                # 饱和度调整（转换到HSV）
                if saturation_factor != 1.0:
                    hsv = self.cv2.cvtColor(enhanced_image, self.cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = hsv[:, :, 1] * saturation_factor
                    enhanced_image = self.cv2.cvtColor(hsv, self.cv2.COLOR_HSV2BGR)
                    adjustments['saturation'] = saturation_factor
                
                # 锐化
                if sharpness_factor > 1.0:
                    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                    sharpened = self.cv2.filter2D(enhanced_image, -1, kernel)
                    enhanced_image = self.cv2.addWeighted(enhanced_image, 2-sharpness_factor, sharpened, sharpness_factor-1, 0)
                    adjustments['sharpness'] = sharpness_factor
                
            else:  # PIL
                # 使用PIL进行增强
                if brightness_factor != 1.0:
                    enhancer = self.pil_enhance.Brightness(enhanced_image)
                    enhanced_image = enhancer.enhance(brightness_factor)
                    adjustments['brightness'] = brightness_factor
                
                if contrast_factor != 1.0:
                    enhancer = self.pil_enhance.Contrast(enhanced_image)
                    enhanced_image = enhancer.enhance(contrast_factor)
                    adjustments['contrast'] = contrast_factor
                
                if saturation_factor != 1.0:
                    enhancer = self.pil_enhance.Color(enhanced_image)
                    enhanced_image = enhancer.enhance(saturation_factor)
                    adjustments['saturation'] = saturation_factor
                
                if sharpness_factor != 1.0:
                    enhancer = self.pil_enhance.Sharpness(enhanced_image)
                    enhanced_image = enhancer.enhance(sharpness_factor)
                    adjustments['sharpness'] = sharpness_factor
            
            return enhanced_image, adjustments
            
        except Exception as e:
            log_error(f"图像增强失败: {e}", "PREPROCESSOR")
            return image, {'error': str(e)}
    
    def _reduce_noise(self, image: Union[np.ndarray, Any], using_opencv: bool) -> Tuple[Union[np.ndarray, Any], Dict[str, Any]]:
        """噪声去除"""
        try:
            config = self.config.get('noise_reduction', {})
            method = config.get('method', 'gaussian_blur')
            kernel_size = config.get('kernel_size', 3)
            sigma = config.get('sigma', 0.5)
            
            processed_image = image
            process_info = {'method': method}
            
            if using_opencv:
                if method == 'gaussian_blur':
                    processed_image = self.cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
                    process_info['kernel_size'] = kernel_size
                    process_info['sigma'] = sigma
                
                elif method == 'median_blur':
                    processed_image = self.cv2.medianBlur(image, kernel_size)
                    process_info['kernel_size'] = kernel_size
                
                elif method == 'bilateral_filter':
                    processed_image = self.cv2.bilateralFilter(image, 9, 75, 75)
                    process_info['parameters'] = (9, 75, 75)
                
                elif method == 'non_local_means':
                    if len(image.shape) == 3:  # 彩色图像
                        processed_image = self.cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
                    else:  # 灰度图像
                        processed_image = self.cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
                    process_info['parameters'] = 'auto'
                
            else:  # PIL
                if method == 'gaussian_blur':
                    processed_image = image.filter(self.pil_filter.GaussianBlur(radius=sigma))
                    process_info['radius'] = sigma
                
                elif method == 'median_blur':
                    processed_image = image.filter(self.pil_filter.MedianFilter(size=kernel_size))
                    process_info['size'] = kernel_size
                
                elif method == 'smooth':
                    processed_image = image.filter(self.pil_filter.SMOOTH)
                    process_info['filter'] = 'SMOOTH'
            
            return processed_image, process_info
            
        except Exception as e:
            log_error(f"噪声去除失败: {e}", "PREPROCESSOR")
            return image, {'error': str(e)}
    
    def _correct_perspective(self, image: Union[np.ndarray, Any], using_opencv: bool) -> Tuple[Union[np.ndarray, Any], Dict[str, Any]]:
        """透视矫正"""
        try:
            if not using_opencv or not self.cv2_available:
                return image, {'error': '透视矫正需要OpenCV支持'}
            
            config = self.config.get('perspective_correction', {})
            auto_detect = config.get('auto_detect', True)
            
            if auto_detect:
                # 自动检测矩形轮廓
                gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
                edges = self.cv2.Canny(gray, 50, 150, apertureSize=3)
                
                contours, _ = self.cv2.findContours(edges, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
                
                # 寻找最大的四边形轮廓
                largest_contour = None
                max_area = 0
                
                for contour in contours:
                    area = self.cv2.contourArea(contour)
                    if area > max_area:
                        # 近似轮廓
                        epsilon = 0.02 * self.cv2.arcLength(contour, True)
                        approx = self.cv2.approxPolyDP(contour, epsilon, True)
                        
                        if len(approx) == 4 and area > 1000:  # 四边形且面积足够大
                            largest_contour = approx
                            max_area = area
                
                if largest_contour is not None:
                    # 执行透视变换
                    src_points = largest_contour.reshape(4, 2).astype(np.float32)
                    
                    # 计算目标矩形的尺寸
                    width = max(
                        np.linalg.norm(src_points[0] - src_points[1]),
                        np.linalg.norm(src_points[2] - src_points[3])
                    )
                    height = max(
                        np.linalg.norm(src_points[0] - src_points[3]),
                        np.linalg.norm(src_points[1] - src_points[2])
                    )
                    
                    dst_points = np.array([
                        [0, 0],
                        [width, 0],
                        [width, height],
                        [0, height]
                    ], dtype=np.float32)
                    
                    # 计算透视变换矩阵
                    matrix = self.cv2.getPerspectiveTransform(src_points, dst_points)
                    
                    # 应用透视变换
                    corrected_image = self.cv2.warpPerspective(image, matrix, (int(width), int(height)))
                    
                    return corrected_image, {
                        'corrected': True,
                        'contour_area': max_area,
                        'output_size': (int(width), int(height))
                    }
                else:
                    return image, {
                        'corrected': False,
                        'reason': '未检测到合适的四边形轮廓'
                    }
            else:
                return image, {
                    'corrected': False,
                    'reason': '手动透视矫正未实现'
                }
            
        except Exception as e:
            log_error(f"透视矫正失败: {e}", "PREPROCESSOR")
            return image, {'error': str(e)}
    
    def _save_image(self, image: Union[np.ndarray, Any], output_path: str, using_opencv: bool) -> bool:
        """保存图像"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if using_opencv:
                return self.cv2.imwrite(str(output_file), image)
            else:
                image.save(str(output_file))
                return True
                
        except Exception as e:
            log_error(f"保存图像失败: {e}", "PREPROCESSOR")
            return False
    
    def get_preprocessor_info(self) -> Dict[str, Any]:
        """获取预处理器信息"""
        return {
            'cv2_available': self.cv2_available,
            'pil_available': self.pil_available,
            'config': self.config,
            'available_steps': [
                'resize', 'enhance', 'noise_reduction', 'perspective_correction'
            ]
        }

if __name__ == "__main__":
    print("🧪 测试图像预处理器")
    
    # 测试配置
    test_config = {
        'pipeline': ['resize', 'enhance', 'noise_reduction'],
        'resize': {
            'enabled': True,
            'target_width': 640,
            'target_height': 480,
            'keep_aspect_ratio': True,
            'interpolation': 'INTER_LINEAR'
        },
        'enhance': {
            'enabled': True,
            'brightness_factor': 1.1,
            'contrast_factor': 1.2,
            'saturation_factor': 1.0,
            'sharpness_factor': 1.1,
            'auto_adjust': True
        },
        'noise_reduction': {
            'enabled': True,
            'method': 'gaussian_blur',
            'kernel_size': 3,
            'sigma': 0.5
        },
        'perspective_correction': {
            'enabled': False,
            'auto_detect': True,
            'corner_detection_method': 'harris'
        }
    }
    
    # 创建预处理器
    preprocessor = ImagePreprocessor(test_config)
    
    # 获取预处理器信息
    info = preprocessor.get_preprocessor_info()
    print(f"预处理器信息: {info}")
    
    print("✅ 图像预处理器测试完成")