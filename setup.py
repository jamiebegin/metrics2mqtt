from distutils.core import setup

setup(
  name = 'metrics2mqtt',
  packages = ['metrics2mqtt'], 
  version = '0.1.10',
  license='MIT', 
  description = 'Publish hardware monitoring data from psutil to a MQTT broker.',  
  author = 'Jamie Begin',
  author_email = 'jjbegin@gmail.com',
  url = 'https://github.com/jamiebegin/metrics2mqtt', 
  download_url = 'https://github.com/jamiebegin/metrics2mqtt/archive/v0.1.10.tar.gz', 
  keywords = ['mqtt', 'psutil', 'metrics'], 
  setup_requires = [
    'wheel'
    ],
  entry_points = {
        'console_scripts': [
            'metrics2mqtt = metrics2mqtt.metrics2mqtt:main'
        ]
  },    
  install_requires=[ 
          'jsons',
          'psutil',
          'paho-mqtt',
      ],
  zip_safe = False,
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Information Technology', 
    'Topic :: System :: Monitoring',
    'Topic :: System :: Logging',
    'Topic :: System :: Systems Administration',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
  ],
)