class VideoExtract < Formula
  include Language::Python::Virtualenv

  desc "AI-powered YouTube video transcript and slide analyzer"
  homepage "https://github.com/philippb/video-extract"
  url "https://github.com/philippb/video-extract/archive/v1.0.0.tar.gz"
  sha256 "dc79d8cb2d21983b425233f71cab8ce21a0847cb7b24def8cf499c8d67ee58fc"
  license "MIT"
  head "https://github.com/philippb/video-extract.git", branch: "main"

  depends_on "python@3.12"
  depends_on "ffmpeg"
  depends_on "tesseract"

  # Python dependencies as resources
  # Generate these with: brew update-python-resources video-extract
  
  resource "openai" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "youtube-transcript-api" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "yt-dlp" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "pillow" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "opencv-python" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "pytesseract" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "tenacity" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "argparse-color-formatter" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "colorama" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "imagehash" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  resource "numpy" do
    url "https://files.pythonhosted.org/packages/PLACEHOLDER"
    sha256 "PLACEHOLDER"
  end

  def install
    # Install Python dependencies in virtual environment
    virtualenv_install_with_resources

    # Create wrapper script that sets up environment
    (bin/"video-extract").write_env_script libexec/"bin/video-extract", {}
    (bin/"vext").write_env_script libexec/"bin/vext", {}

    # Install .env.example file for reference
    pkgshare.install ".env.example"
  end

  def post_install
    # Create config directory and copy example config if needed
    config_dir = "#{Dir.home}/.video-extract"
    FileUtils.mkdir_p(config_dir)
    
    env_file = "#{config_dir}/.env"
    unless File.exist?(env_file)
      FileUtils.cp("#{pkgshare}/.env.example", env_file)
      puts <<~EOS
        📋 Configuration file created at: #{env_file}
        
        To get started:
        1. Run: video-extract init
        2. Add your OpenAI API key to the configuration
        3. Process videos with: video-extract <VIDEO_ID>
      EOS
    end
  end

  test do
    # Test that the CLI loads without errors
    system bin/"video-extract", "--help"
    
    # Test that dependencies are available
    system Formula["ffmpeg"].opt_bin/"ffmpeg", "-version"
    system Formula["tesseract"].opt_bin/"tesseract", "--version"
    
    # Test that Python modules can be imported
    system libexec/"bin/python", "-c", "import openai, cv2, pytesseract"
  end

  def caveats
    <<~EOS
      To get started with video-extract:

      1. Initialize with API key setup:
         video-extract init

      2. Process a video:
         video-extract <YOUTUBE_VIDEO_ID>

      3. Edit settings anytime:
         video-extract config

      Get your OpenAI API key from:
      https://platform.openai.com/api-keys

      For more information, see:
      #{homepage}
    EOS
  end
end