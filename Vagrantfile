# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/centos-8.0"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder "images", "/opt/images"
  config.vm.synced_folder "patches", "/opt/patches"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
  end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  config.vm.provision "shell", inline: <<-SHELL
    # Dependencies.
    yum -y upgrade
    yum -y groupinstall "development tools"
    yum -y install python2 gtk2-devel vim-enhanced tmux

    # Fetch and install ARM cross-compilers (for GDB).
    curl -sLo /tmp/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2 \
      https://developer.arm.com/-/media/Files/downloads/gnu-rm/9-2019q4/RC2.1/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
    tar -xjvf /tmp/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2 \
      -C /opt/

    # Add to PATH for all users.
    echo 'export PATH=/opt/gcc-arm-none-eabi-9-2019-q4-major/bin:$PATH' > \
      /etc/profile.d/99-arm.sh

    # Fetch qemu_stm32.
    git clone https://github.com/beckus/qemu_stm32.git \
      /usr/local/src/qemu_stm32/
    cd /usr/local/src/qemu_stm32/
    
    # Ensure we're on a compatible version.
    git checkout 96ba2f18bab98240f8af0a88010f31dfecf8322a
    git submodule init
    git submodule update --recursive

    # Patch.
    for patch in /opt/patches/*.patch; do
      patch -p0 < $patch
    done

    # Build and install.
    CFLAGS="-Wno-error" ./configure \
      --target-list=arm-softmmu,armeb-linux-user,arm-linux-user \
      --python=`which python2`
    make -j2
    make install
  SHELL
end
