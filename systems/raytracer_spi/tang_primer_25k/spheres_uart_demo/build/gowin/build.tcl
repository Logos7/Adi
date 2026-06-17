set project_name spheres_uart_demo
open_project [file join $project_name ${project_name}.gprj]
run all
close_project
puts "Adi sphere raytracer 25K build finished."
