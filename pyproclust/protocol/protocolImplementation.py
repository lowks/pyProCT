'''
Created on 21/05/2012

@author: victor
'''
from pyRMSD.matrixHandler import MatrixHandler
from pyproclust.tools.plotTools import matrixToImage
from pyproclust.protocol.TimerHandler import TimerHandler
from pyproclust.protocol.observer.observable import Observable
import pyproclust.protocol.scheduling.tools as scheduling_tools
from pyproclust.protocol.workspaceHandler import WorkspaceHandler
from pyproclust.protocol.trajectoryHandler import TrajectoryHandler 
from pyproclust.clustering.comparison.distrprob.kullbackLieblerDivergence import KullbackLeiblerDivergence
from pyproclust.protocol.exploration.clusteringExplorator import ClusteringExplorator
from pyproclust.clustering.filtering.clusteringFilter import ClusteringFilter
from pyproclust.clustering.analysis.picklingAnalysisRunner import PicklingAnalysisRunner
from pyproclust.clustering.analysis.analysisPopulator import AnalysisPopulator
from pyproclust.clustering.selection.bestClusteringSelector import BestClusteringSelector


class Protocol(Observable):

    def __init__(self, observer):
        super(Protocol,self).__init__(observer)
        
    def run(self, parameters):
        
        #####################
        # Start timing 
        #####################
        self.timer = TimerHandler()
        self.timer.start("Global")
        
        #####################
        # Create workspace 
        #####################
        self.workspaceHandler = WorkspaceHandler(parameters, self.observer)
        self.workspaceHandler.create_directories()

        #####################
        # Loading trajectory 
        #####################
        self.timer.start("Trajectory Loading")
        self.trajectoryHandler = TrajectoryHandler(parameters, self.observer)
        self.timer.stop("Trajectory Loading")
        
        ##############################
        # Obtaining the distance matrix
        ##############################
        self.matrixHandler = MatrixHandler(self.workspaceHandler["matrix"])
        if parameters["matrix"]["creation"] == "load":
            self.timer.start("Matrix Loading")
            self.matrixHandler.loadMatrix(self.evaluation_parameters["matrix_path"])
            self.timer.stop("Matrix Loading")
            
        elif parameters["matrix"]["creation"] == "calculate":
            self.timer.start("Matrix Calculation")
            self.matrixHandler.createMatrix(self.trajectoryHandler.coordsets,"QTRFIT_OMP_CALCULATOR")
            self.timer.stop("Matrix Calculation")
            
        else:
            print "[Error] Incorrect matrix creation option: "+parameters["matrix"]["creation"]
            return 
           
        if parameters["matrix"]["save_matrix"]:
            self.timer.start("Matrix Save")
            self.matrixHandler.saveMatrix(parameters["store_matrix_path"])
            self.timer.stop("Matrix Save")
        
        ############################################
        # Distribution analysis
        ############################################
        if parameters["matrix"]["action"] == "comparison":
            self.timer.start("KL divergence")
            klDiv = KullbackLeiblerDivergence(self.trajectoryHandler.pdbs, self.matrixHandler.distance_matrix)
            klDiv.save(self.workspaceHandler["matrix"]+"/kullback_liebler_divergence")
            self.timer.stop("KL divergence")
        print self.timer.get_elapsed()
        
        #########################
        # Matrix plot
        #########################
        self.timer.start("Matrix Imaging")
        matrixToImage(self.matrixHandler.distance_matrix,
                      self.workspaceHandler["matrix"]+"/matrix_plot.png",
                      max_dim = 1000,
                      observer = self.observer)
        self.timer.stop("Matrix Imaging")
        
        ############################
        # Clustering exploration
        ############################
        self.timer.start("Clustering Exploration")
        clusterings  = ClusteringExplorator(parameters, 
                                           self.matrixHandler, 
                                           self.workspaceHandler, 
                                           scheduling_tools.build_scheduler("Process/Parallel",
                                                           parameters["control"]["algorithm_scheduler_sleep_time"],
                                                           self.observer,
                                                           parameters["control"]["number_of_processors"]), 
                                           self.observer).run()
        self.notify("Clusterings Created", {"number_of_clusters":len(clusterings)})
        self.timer.stop("Clustering Exploration")
        
        ######################
        # First filtering
        ######################
        self.timer.start("Clustering Filtering")
        selected_clusterings, not_selected_clusterings = ClusteringFilter(parameters["evaluation"], 
                                                                          self.matrixHandler).filter(clusterings)
            
        self.notify("Filter", {"selected":selected_clusterings,"not_selected":not_selected_clusterings})
        self.timer.stop("Clustering Filtering")
        
        if selected_clusterings == []:
            self.notify("SHUTDOWN", "The clustering search gave no clusterings. Relax evaluation constraints.")
        else:      
            ######################
            # Clustering scoring
            ######################
            self.timer.start("Evaluation")
            analyzer = PicklingAnalysisRunner(scheduling_tools.build_scheduler("Process/Parallel",
                                                           parameters["control"]["algorithm_scheduler_sleep_time"],
                                                           self.observer,
                                                           parameters["control"]["number_of_processors"]),
                                              parameters,
                                              selected_clusterings,
                                              AnalysisPopulator(self.matrixHandler, 
                                                                self.trajectoryHandler,
                                                                parameters))
            
            analyzer.evaluate()
            self.timer.stop("Evaluation")
            
            ######################
            # Choose the best clustering
            ######################
            self.timer.start("Selection")
            best_clustering_id, best_criteria_id, best_score = BestClusteringSelector(parameters).choose_best(selected_clusterings)
            self.notify("BEST", (best_clustering_id, best_criteria_id, best_score))
            self.timer.stop("Selection")


#             ######################
#             # Bake up results
#             ######################
#             save_results(protocol_params,self.workspaceHandler.results_path,string_results,results_pack)
#             self.htmlReport.report["Evaluations"] = results_pack
# #            result_pack_file_handler = open(self.workspaceHandler.results_path+"/"+protocol_params.report_file+".bin","r")
# #            results_pack = pickle.load(result_pack_file_handler)
# #            result_pack_file_handler.close()
#             
#             
#             #########################
#             # Get statistics etc...
#             #########################
#             if protocol_params.most_representative_pdb_file != "":
#                 save_most_representative(protocol_params,best_clustering,\
#                                         self.matrixHandler.distance_matrix,\
#                                         self.workspaceHandler.tmp_path,\
#                                         self.workspaceHandler.results_path)
#             
#             
#             analyzer = ClusteringStatisticalAnalyzer(best_clustering,\
#                                                      protocol_params.pdb1,\
#                                                      protocol_params.pdb2,\
#                                                      self.matrixHandler.distance_matrix,\
#                                                      protocol_params.shallWeCompareTrajectories())
#             analyzer.per_cluster_analytics()
#             
#             analyzer.per_clustering_analytics()
#             
#             plotGenerator = ClusteringPlotsGenerator(analyzer)
#             
#             big_plot = plotGenerator.generate_and_compose_big_plot(composition_size= (1024,720), max_radius = 150, ball_horizontal_separation = 50, ball_vertical_separation = 100)
#             
#             if protocol_params.shallWeCompareTrajectories():
#                 small_plot = plotGenerator.generate_and_compose_small_plot(composition_size= (400,700))
#             else:
#                 small_plot = plotGenerator.generate_and_compose_small_plot(composition_size= (400,300))
#             
#             big_plot.save(self.workspaceHandler.results_path+"/analysis_plot_big.png")
#             small_plot.save(self.workspaceHandler.results_path+"/analysis_plot_small.png")
#             
#         global_time_end = time.time()
#         self.htmlReport.report["Timing"] += 'All the process took %0.3f s\n' % (global_time_end-global_time_start)
#         
#         time_file = open(self.workspaceHandler.tmp_path+"/timing.txt","w")
#         time_file.write(self.htmlReport.report["Timing"])
#         time_file.close()
#         
#         
#         #HTML REPORT
#         html_file = open(self.workspaceHandler.results_path+"/report.html","w")
#         html_file.write(self.htmlReport.generateHTML())
#         html_file.close()
#         
#         #IMAGES FOR REPORT
#         self.htmlReport.report["Image Paths"]["kl"] = self.workspaceHandler.matrix_path+"/rmsd_distrib.png"
#         self.htmlReport.report["Image Paths"]["matrix"] = self.workspaceHandler.matrix_path+"/matrix_plot.png"
#         self.htmlReport.report["Image Paths"]["clustering_small"] = self.workspaceHandler.results_path+"/analysis_plot_small.png"
#         self.htmlReport.report["Image Paths"]["clustering_big"] = self.workspaceHandler.results_path+"/analysis_plot_big.png"
#         self.htmlReport.create_thumbnails(self.workspaceHandler.results_path)
#     
#    
        
    