from spin import spin_config
import tempfile


def test_spinrc_yaml_bounce():
    spinrc = spin_config.SpinRc(
        user=spin_config.SpinRcUser(name="Kevin Bache", email="kevin.bache@gmail.com", github_username='kevinbache'),
        projects=[spin_config.SpinRcProject(project_dir='/Users/bache/projects/dervish/')]
    )

    with tempfile.NamedTemporaryFile() as my_temp_file:
        spinrc.to_yaml(my_temp_file.name)
        spinrc2 = spin_config.SpinRc.from_yaml(my_temp_file.name)

    assert spinrc == spinrc2


if __name__ == '__main__':
    test_spinrc_yaml_bounce()
