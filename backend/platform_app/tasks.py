import shutil
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .models import Lesson, LessonVideo


QUALITY_PROFILES = [
    {'name': '480p', 'height': 480, 'bandwidth': 1400000, 'resolution': '854x480'},
    {'name': '720p', 'height': 720, 'bandwidth': 2800000, 'resolution': '1280x720'},
    {'name': '1080p', 'height': 1080, 'bandwidth': 5000000, 'resolution': '1920x1080'},
]


def _master_manifest_content():
    lines = ['#EXTM3U', '#EXT-X-VERSION:3']
    for profile in QUALITY_PROFILES:
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={profile["bandwidth"]},RESOLUTION={profile["resolution"]}'
        )
        lines.append(f'{profile["name"]}.m3u8')
    return '\n'.join(lines) + '\n'


@shared_task(bind=True)
def convert_to_hls(self, lesson_id, video_file_path):
    lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    lesson_video, _ = LessonVideo.objects.get_or_create(lesson=lesson)
    lesson_video.status = LessonVideo.STATUS_PROCESSING
    lesson_video.error_message = ''
    lesson_video.save(update_fields=['status', 'error_message', 'updated_at'])

    output_dir = Path(settings.MEDIA_ROOT) / 'hls' / f'lesson_{lesson_id}'
    output_dir_rel = f'hls/lesson_{lesson_id}/master.m3u8'

    try:
        try:
            import ffmpeg
        except ImportError as exc:
            raise RuntimeError('Модуль ffmpeg-python не установлен') from exc

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for profile in QUALITY_PROFILES:
            variant_name = profile['name']
            variant_playlist = output_dir / f'{variant_name}.m3u8'
            segment_pattern = output_dir / f'{variant_name}_%03d.ts'

            (
                ffmpeg
                .input(video_file_path)
                .output(
                    str(variant_playlist),
                    vf=f'scale=-2:{profile["height"]}',
                    vcodec='libx264',
                    acodec='aac',
                    audio_bitrate='128k',
                    preset='veryfast',
                    crf=21,
                    hls_time=6,
                    hls_playlist_type='vod',
                    hls_segment_filename=str(segment_pattern),
                    format='hls',
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

        master_manifest_path = output_dir / 'master.m3u8'
        master_manifest_path.write_text(_master_manifest_content(), encoding='utf-8')

        lesson_video.status = LessonVideo.STATUS_READY
        lesson_video.m3u8_url = f'{settings.MEDIA_URL}{output_dir_rel}'.replace('//', '/')
        lesson_video.error_message = ''
        lesson_video.save(update_fields=['status', 'm3u8_url', 'error_message', 'updated_at'])
    except Exception as exc:  # pragma: no cover - depends on ffmpeg/worker env
        lesson_video.status = LessonVideo.STATUS_FAILED
        lesson_video.error_message = str(exc)[:2000]
        lesson_video.save(update_fields=['status', 'error_message', 'updated_at'])
        raise
    finally:
        source_path = Path(video_file_path)
        if source_path.exists():
            source_path.unlink()
