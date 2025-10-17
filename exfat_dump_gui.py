import sys
import subprocess
import shlex
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QCheckBox,
    QTextEdit, QFileDialog, QGroupBox, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt

class ExFATDumpGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("exFAT_dump v0.3 GUI")
        self.setGeometry(100, 100, 1000, 750)
        # --- IMPORTANT: Set the correct path to your exfat_dump.py script ---
        self.script_path = "exfat_dump.py" 
        self.init_ui()

    def init_ui(self):
        # --- Main Layout (Vertical) ---
        main_layout = QVBoxLayout(self)

        # --- Top Section: Input and Command (Grid Layout) ---
        input_group = QGroupBox("Input and Command Selection")
        input_layout = QGridLayout()

        # 1. Image File Input
        self.image_file_input = QLineEdit()
        self.image_file_input.setPlaceholderText("Select the disk image file (e.g., C:\\disk.img or exfat12.001)")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_image_file)
        
        input_layout.addWidget(QLabel("Image File:"), 0, 0)
        input_layout.addWidget(self.image_file_input, 0, 1)
        input_layout.addWidget(browse_button, 0, 2)

        # 2. Command Selection
        self.command_select = QComboBox()
        self.commands = ['mmls', 'fls', 'fsstat', 'icat', 'istat']
        self.command_select.addItems(self.commands)
        self.command_select.currentIndexChanged.connect(self.update_fields) 

        input_layout.addWidget(QLabel("Command:"), 1, 0)
        input_layout.addWidget(self.command_select, 1, 1, 1, 2)

        # 3. Entry Number/Offset Input
        self.entry_number_input = QLineEdit()
        self.entry_number_input.setPlaceholderText("File Entry Number (icat/istat) OR Offset Value (for -o)")
        self.entry_number_input.setEnabled(False) 
        
        input_layout.addWidget(QLabel("Entry/Offset Value:"), 2, 0)
        input_layout.addWidget(self.entry_number_input, 2, 1, 1, 2)
        
        # 4. Debug Level Input
        self.debug_level_label = QLabel("Debug Level (-d):")
        self.debug_level_spinbox = QSpinBox()
        self.debug_level_spinbox.setRange(0, 2)
        self.debug_level_spinbox.setValue(0) # Default is 0
        
        input_layout.addWidget(self.debug_level_label, 3, 0)
        input_layout.addWidget(self.debug_level_spinbox, 3, 1)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # --- Middle Section: Options and Run Button (Horizontal Layout) ---
        
        # Options Group
        options_group = QGroupBox("Flags")
        options_layout = QHBoxLayout()
        
        # -o is handled as a simple flag here, with the value taken from the entry_number_input
        self.option_o = QCheckBox("-o (Partition Offset Flag)")
        self.option_o.stateChanged.connect(self.update_fields_for_offset)
        self.option_l = QCheckBox("-l (Long/Detailed)")   
        self.option_r = QCheckBox("-r (Recursively Lists)")
        self.option_h = QCheckBox("-h (Compute SHA1)")    
        
        options_layout.addWidget(self.option_o)
        options_layout.addWidget(self.option_l)
        options_layout.addWidget(self.option_r)
        options_layout.addWidget(self.option_h)
        options_group.setLayout(options_layout)
        
        options_run_layout = QHBoxLayout()
        options_run_layout.addWidget(options_group)

        # Run Button
        self.run_button = QPushButton("Run")
        self.run_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.run_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: #4CAF50; color: white;")
        self.run_button.clicked.connect(self.execute_exfat_dump)
        options_run_layout.addWidget(self.run_button)
        
        main_layout.addLayout(options_run_layout)

        # --- Bottom Section: Output Display ---
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Output will appear here after execution...")
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        
        main_layout.addWidget(output_group)
        main_layout.setStretchFactor(output_group, 1)
        
        # Initial field update
        self.update_fields(self.command_select.currentIndex())
    
    # ------------------ Methods ------------------

    def browse_image_file(self):
        """Opens a file dialog to select the image file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Disk Image File", 
            "", 
            "All Files (*);;Disk Images (*.img *.dd)"
        )
        if file_name:
            self.image_file_input.setText(file_name)
    
    def update_fields_for_offset(self, state):
        """Enable/disable entry field when -o is checked, or if icat/istat is selected."""
        self.entry_number_input.setEnabled(self.option_o.isChecked() or self.command_select.currentText() in ('icat', 'istat'))

    def update_fields(self, index):
        """Enables/Disables fields and options based on the selected command."""
        command = self.commands[index]
        
        # 1. Entry Number/Offset Field Logic
        self.entry_number_input.setEnabled(self.option_o.isChecked() or command in ('icat', 'istat'))
        
        # 2. Options Checkbox Logic
        self.option_o.setEnabled(command != 'mmls')
        
        is_fls = command == 'fls'
        self.option_l.setEnabled(is_fls)
        self.option_r.setEnabled(is_fls)
        
        is_icat = command == 'icat'
        self.option_h.setEnabled(is_icat)

    def build_command(self):
        """Constructs the complete command list: python exfat_dump.py <command> [FLAGS and VALUES] <imagefile> [entry_number]"""
        
        image_file = self.image_file_input.text().strip()
        command = self.command_select.currentText()
        input_value = self.entry_number_input.text().strip() # This holds the offset OR entry_number
        debug_level = self.debug_level_spinbox.value()

        if not image_file:
            self.output_text.setText("<span style='color:red;'>ERROR: Please select an Image File.</span>")
            return None

        # Base command: python exfat_dump.py <command>
        cmd_list = ["python", self.script_path, command]

        # 1. Add FLAGS and their VALUES
        
        # Debug Level (-d <level>)
        if debug_level > 0:
            cmd_list.append("-d")
            cmd_list.append(str(debug_level))
        
        # Partition Offset (-o <offset>) - ONLY IF CHECKED
        if self.option_o.isChecked() and self.option_o.isEnabled():
            if not input_value or not input_value.isdigit():
                 self.output_text.setText("<span style='color:red;'>ERROR: The -o flag requires a numerical offset value in the Entry/Offset field.</span>")
                 return None
            cmd_list.append("-o")
            cmd_list.append(input_value) # Value follows the -o flag
        
        # Other simple flags
        if self.option_l.isChecked() and self.option_l.isEnabled():
            cmd_list.append("-l")
        if self.option_r.isChecked() and self.option_r.isEnabled():
            cmd_list.append("-r")
        if self.option_h.isChecked() and self.option_h.isEnabled():
            cmd_list.append("-h")
            
        # 2. Add POSITIONAL ARGUMENTS
        
        # The Image File (The first positional argument after all flags)
        cmd_list.append(image_file)

        # The Entry Number (Only for icat/istat and optional for fls, and NOT if used as -o value)
        if command in ('fls', 'icat', 'istat') and not self.option_o.isChecked():
            if command in ('icat', 'istat'):
                if not input_value or not input_value.isdigit():
                    self.output_text.setText("<span style='color:red;'>ERROR: 'icat' and 'istat' require a numerical Entry Number.</span>")
                    return None
                cmd_list.append(input_value)
            
            elif command == 'fls' and input_value and input_value.isdigit():
                # Allow entry number for fls if provided and not being used as -o value
                cmd_list.append(input_value)
                
        return cmd_list

    def execute_exfat_dump(self):
        """Executes the exfat_dump.py script using the subprocess module."""
        
        cmd_list = self.build_command()
        if cmd_list is None:
            return

        # Display the command being run
        command_string = ' '.join(shlex.quote(arg) for arg in cmd_list)
        self.output_text.setText(f"Executing: {command_string}\n\nProcessing...")
        
        try:
            # Execute the command and wait for it to complete
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                timeout=300
            )
            
            # Display successful output
            output = f"--- COMMAND EXECUTED SUCCESSFULLY ---\n\n{result.stdout}"
            self.output_text.setText(output)

        except subprocess.CalledProcessError as e:
            # Display command error
            error_msg = f"--- ERROR EXECUTING COMMAND (Return Code: {e.returncode})---\n"
            error_msg += f"Command: {command_string}\n\n"
            error_msg += f"<span style='color:red;'>STDERR:</span>\n{e.stderr.strip()}\n\n"
            error_msg += f"<span style='color:blue;'>STDOUT (Partial):</span>\n{e.stdout.strip()}"
            self.output_text.setText(error_msg)

        except subprocess.TimeoutExpired:
            self.output_text.setText(f"<span style='color:red;'>ERROR: Command timed out after 5 minutes.</span>")
            
        except FileNotFoundError:
            # Display interpreter/script path error
            error_msg = f"<span style='color:red;'>FATAL ERROR: Could not find Python interpreter or the script.</span>\n"
            error_msg += f"Check if 'python' is in your PATH or if '{self.script_path}' exists in the correct location."
            self.output_text.setText(error_msg)
            
        except Exception as e:
            # Catch other unexpected exceptions
            self.output_text.setText(f"<span style='color:red;'>UNEXPECTED ERROR:</span>\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = ExFATDumpGUI()
    gui.show()
    sys.exit(app.exec())